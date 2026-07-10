"""Deliver the brief via the Telegram Bot API (outbound HTTPS only)."""

from __future__ import annotations

import logging
import os

import httpx

from .models import Item

log = logging.getLogger(__name__)


def keyboard(top: list[Item]) -> dict | None:
    """Reply keyboard: a tap sends the label as a normal message, which
    Telegram retains 24h for the morning poll — unlike callback queries,
    which expire within minutes (learned the hard way)."""
    if not top:
        return None
    return {
        "keyboard": [[f"{i} 👍", f"{i} 👎", f"{i} 🔖"] for i in range(1, len(top) + 1)],
        "resize_keyboard": True,
        "input_field_placeholder": "Rate today's brief",
    }


def send(chunks: list[str], reply_markup: dict | None = None) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with httpx.Client(timeout=20) as client:
        for i, chunk in enumerate(chunks):
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            if reply_markup and i == len(chunks) - 1:  # keyboard is chat-level: set it last
                payload["reply_markup"] = reply_markup
            resp = client.post(url, json=payload)
            resp.raise_for_status()
    log.info("delivered %d message(s)", len(chunks))
