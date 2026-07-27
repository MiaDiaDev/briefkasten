"""Harvest reply-keyboard feedback via getUpdates — serverless-friendly.

A keyboard tap sends a normal message like "2 👍", which Telegram retains
24h (callback queries expire within minutes, so inline buttons are out
until there is a real webhook endpoint). Each daily run polls once before
composing the brief and resolves ranks against history.jsonl. Only
messages from the owner's chat id are accepted; everything else advances
the offset and is dropped.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .state import HISTORY

log = logging.getLogger(__name__)
FEEDBACK = Path(__file__).parents[2] / "data" / "feedback.jsonl"
CARD_REPLIES = Path(__file__).parents[2] / "data" / "card_replies.jsonl"
OFFSET = Path(__file__).parents[2] / "data" / "tg_offset.json"
ACTIONS = {"👍": "up", "👎": "down", "🔖": "save"}
PATTERN = re.compile(r"^\s*([1-9])\s*(👍|👎|🔖)\s*$")  # legacy explicit form still works
BARE_NUMBER = re.compile(r"^\s*([1-9])\s*$")  # bare rank reply = save that item
MAX_REPLY_CHARS = 500


def poll(consume: bool = True) -> list[dict]:
    """Fetch pending updates; if `consume`, persist events and the offset."""
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

    taps, texts, max_id = parse_updates(updates, chat_id)
    rows = resolve(taps, _load_history())
    if consume and rows:
        with FEEDBACK.open("a") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
    if consume and texts:  # evening-card answers/check-ins, graded by card.py
        with CARD_REPLIES.open("a") as f:
            for t in texts:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        log.info("stored %d card reply/replies", len(texts))
    if consume and max_id > offset:
        OFFSET.write_text(json.dumps({"offset": max_id}))
    return rows


def parse_updates(
    updates: list[dict], chat_id: str
) -> tuple[list[dict], list[dict], int]:
    """Split owner messages into brief-feedback taps and everything else.

    Returns (taps, texts, max_id): taps are {"msg_date", "rank", "action"},
    texts are {"date", "text"} — evening-card answers and check-ins."""
    taps: list[dict] = []
    texts: list[dict] = []
    max_id = 0
    for u in updates:
        max_id = max(max_id, u.get("update_id", 0))
        msg = u.get("message")
        if not msg or str(msg.get("from", {}).get("id")) != str(chat_id):
            continue
        text = msg.get("text", "")
        if not text:
            continue
        msg_date = datetime.fromtimestamp(msg["date"], tz=timezone.utc).date().isoformat()
        if m := PATTERN.match(text):
            taps.append(
                {"msg_date": msg_date, "rank": int(m.group(1)), "action": ACTIONS[m.group(2)]}
            )
        elif m := BARE_NUMBER.match(text):
            taps.append({"msg_date": msg_date, "rank": int(m.group(1)), "action": "save"})
        else:
            texts.append({"date": msg_date, "text": text[:MAX_REPLY_CHARS]})
    return taps, texts, max_id


def resolve(taps: list[dict], history: list[dict]) -> list[dict]:
    """Map (msg date, rank) -> item id via the latest brief on or before the
    message date. Same-day reruns overwrite ranks, so the newest brief wins —
    matching the keyboard the owner actually tapped."""
    by_date: dict[str, dict[int, dict]] = {}
    for row in history:
        if row.get("rank"):
            by_date.setdefault(row["date"], {})[row["rank"]] = row

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for tap in taps:
        dates = [d for d in by_date if d <= tap["msg_date"]]
        item = by_date[max(dates)].get(tap["rank"]) if dates else None
        if not item:
            log.warning("unresolved feedback: rank %d on %s", tap["rank"], tap["msg_date"])
            continue
        rows.append({"harvested": now, "action": tap["action"], "item_id": item["id"]})
    return rows


def _load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    return [json.loads(ln) for ln in HISTORY.read_text().splitlines() if ln]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # urls contain the bot token
    for row in poll(consume=False):  # peek: no writes, nothing consumed
        print(row)
