"""Seen-item store and dedupe. Plain JSON, committed back to the repo by CI."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

from .models import Item

STATE = Path(__file__).parents[2] / "data" / "seen.json"
HISTORY = Path(__file__).parents[2] / "data" / "history.jsonl"
RETENTION_DAYS = 30
HISTORY_RETENTION_DAYS = 90
TITLE_SIMILARITY = 0.9


def load_seen(path: Path = STATE) -> dict[str, str]:
    """id -> first-seen ISO timestamp."""
    if not path.exists():
        return {}
    return json.loads(path.read_text() or "{}")


def filter_new(items: list[Item], seen: dict[str, str]) -> list[Item]:
    return [it for it in items if it.id not in seen]


def _norm_title(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def _links_to(a: Item, b: Item) -> bool:
    """a's text contains b's URL (e.g. a tweet announcing a blog post)."""
    target = b.url.split("://")[-1].split("?")[0].split("#")[0].rstrip("/").lower()
    if "/" not in target:  # bare domain would match any mention of the site
        return False
    return target in f"{a.title} {a.summary_raw}".lower()


def _same_story(a: Item, b: Item, ta: str, tb: str) -> bool:
    if ta and tb:
        shorter, longer = sorted((ta, tb), key=len)
        if len(shorter) >= 15 and shorter in longer:
            return True
        if SequenceMatcher(None, ta, tb).ratio() >= TITLE_SIMILARITY:
            return True
    return _links_to(a, b) or _links_to(b, a)


def dedupe(items: list[Item]) -> list[Item]:
    """Collapse the same story reported by several sources within one run.

    Two items are duplicates if their titles fuzzy-match or one links to the
    other's URL. Per cluster, keep the most canonical item: the one others
    link to (the blog post, not the tweet about it), then highest source
    weight, then fetch order (blogs come before twitter sources).
    """
    titles = [_norm_title(it.title) for it in items]
    linked_by = [0] * len(items)
    for i, j in combinations(range(len(items)), 2):
        linked_by[j] += _links_to(items[i], items[j])
        linked_by[i] += _links_to(items[j], items[i])

    order = sorted(
        range(len(items)),
        key=lambda i: (-linked_by[i], -items[i].source_weight, i),
    )
    kept: list[int] = []
    for i in order:
        if not any(_same_story(items[i], items[k], titles[i], titles[k]) for k in kept):
            kept.append(i)
    return [items[i] for i in sorted(kept)]


def append_history(
    brief_date: str,
    items: list[Item],
    ranks: dict[str, int] | None = None,
    path: Path = HISTORY,
) -> None:
    """Log scored items per run; substrate for feedback, stats, deep-dives.

    `ranks` maps item id -> position in the brief's top list, so a reply
    like "2 👍" can be resolved back to an item the next morning."""
    ranks = ranks or {}
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=HISTORY_RETENTION_DAYS)
    ).date().isoformat()
    rows = []
    if path.exists():
        rows = [json.loads(ln) for ln in path.read_text().splitlines() if ln]
        rows = [r for r in rows if r["date"] >= cutoff]
    rows.extend(
        {
            "date": brief_date,
            "rank": ranks.get(it.id),
            "id": it.id,
            "title": it.title,
            "url": it.url,
            "source": it.source,
            "field_impact": it.field_impact,
            "work_relevance": it.work_relevance,
            "personal_interest": it.personal_interest,
            "score": it.score,
            "summary": it.summary,
        }
        for it in items
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


def mark_seen(items: list[Item], seen: dict[str, str], path: Path = STATE) -> None:
    now = datetime.now(timezone.utc)
    for it in items:
        seen[it.id] = now.isoformat()
    cutoff = now - timedelta(days=RETENTION_DAYS)
    pruned = {
        k: v for k, v in seen.items() if datetime.fromisoformat(v) >= cutoff
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pruned, indent=0, sort_keys=True))
