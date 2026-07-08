"""Seen-item store. Plain JSON, committed back to the repo by CI."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Item

STATE = Path(__file__).parents[2] / "data" / "seen.json"
RETENTION_DAYS = 30


def load_seen(path: Path = STATE) -> dict[str, str]:
    """id -> first-seen ISO timestamp."""
    if not path.exists():
        return {}
    return json.loads(path.read_text() or "{}")


def filter_new(items: list[Item], seen: dict[str, str]) -> list[Item]:
    return [it for it in items if it.id not in seen]


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
