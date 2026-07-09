"""Harvest inline-button feedback via getUpdates — serverless-friendly.

Each daily run polls once before composing the brief, so a button press is
recorded up to ~24h later. No webhook, no always-on process. Only events
from the owner's chat id are accepted; everything else advances the offset
and is dropped.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

log = logging.getLogger(__name__)
FEEDBACK = Path(__file__).parents[2] / "data" / "feedback.jsonl"
OFFSET = Path(__file__).parents[2] / "data" / "tg_offset.json"
ACTIONS = {"up", "down", "save"}


def poll(save_offset: bool = True) -> list[dict]:
    """Fetch pending updates, append button events, advance the offset."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    offset = 0
    if OFFSET.exists():
        offset = json.loads(OFFSET.read_text()).get("offset", 0)

    resp = httpx.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={"offset": offset + 1},
        timeout=20,
    )
    resp.raise_for_status()
    updates = resp.json().get("result", [])

    rows, max_id = parse_updates(updates, chat_id)
    if rows:
        with FEEDBACK.open("a") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
    if save_offset and max_id > offset:
        OFFSET.write_text(json.dumps({"offset": max_id}))
    return rows


def parse_updates(updates: list[dict], chat_id: str) -> tuple[list[dict], int]:
    rows: list[dict] = []
    max_id = 0
    now = datetime.now(timezone.utc).isoformat()
    for u in updates:
        max_id = max(max_id, u.get("update_id", 0))
        cq = u.get("callback_query")
        if not cq or str(cq.get("from", {}).get("id")) != str(chat_id):
            continue
        action, _, item_id = (cq.get("data") or "").partition(":")
        if action in ACTIONS and item_id:
            rows.append({"harvested": now, "action": action, "item_id": item_id})
    return rows, max_id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # urls contain the bot token
    for row in poll(save_offset=False):  # peek without consuming
        print(row)
