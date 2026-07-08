"""Fetch items from all configured feeds. Fail soft per source."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import yaml

from .models import Item

log = logging.getLogger(__name__)
CONFIG = Path(__file__).parents[2] / "config" / "sources.yaml"


def _item_id(url: str) -> str:
    """Stable id from a normalized URL (strip tracking params, trailing slash)."""
    clean = url.split("?")[0].split("#")[0].rstrip("/").lower()
    return hashlib.sha256(clean.encode()).hexdigest()[:16]


def fetch_all(config_path: Path = CONFIG) -> list[Item]:
    cfg = yaml.safe_load(config_path.read_text())
    settings = cfg.get("settings", {})
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.get("max_age_hours", 36)
    )
    max_per_source = settings.get("max_items_per_source", 25)

    items: list[Item] = []
    sources = cfg.get("blogs", []) + cfg.get("twitter", [])
    for src in sources:
        try:
            items.extend(_fetch_source(src, cutoff, max_per_source))
        except Exception:  # noqa: BLE001 — one dead feed must not kill the run
            log.exception("source failed: %s", src.get("name"))
    log.info("fetched %d items from %d sources", len(items), len(sources))
    return items


def _fetch_source(src: dict, cutoff: datetime, limit: int) -> list[Item]:
    feed = feedparser.parse(src["url"])
    out: list[Item] = []
    for entry in feed.entries[:limit]:
        published = _entry_time(entry)
        if published and published < cutoff:
            continue
        url = entry.get("link", "")
        if not url:
            continue
        out.append(
            Item(
                id=_item_id(url),
                title=entry.get("title", "(untitled)").strip(),
                url=url,
                source=src["name"],
                source_weight=float(src.get("weight", 1.0)),
                published=published.isoformat() if published else "",
                summary_raw=entry.get("summary", "")[:1500],
            )
        )
    return out


def _entry_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for it in fetch_all():
        print(f"[{it.source}] {it.title}  {it.url}")
