"""Deliver the brief via the Telegram Bot API (outbound HTTPS only)."""

from __future__ import annotations

import logging
import os

import httpx

from .models import Item

log = logging.getLogger(__name__)


def keyboard(top: list[Item]) -> dict | None:
    """Inline feedback buttons, one row per top item. callback_data is
    harvested by feedback.poll() at the start of the next run."""
    if not top:
        return None
    return {
        "inline_keyboard": [
            [
                {"text": f"{i} 👍", "callback_data": f"up:{it.id}"},
                {"text": "👎", "callback_data": f"down:{it.id}"},
                {"text": "🔖", "callback_data": f"save:{it.id}"},
            ]
            for i, it in enumerate(top, 1)
        ]
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
            if reply_markup and i == 0:  # buttons belong to the top-items chunk
                payload["reply_markup"] = reply_markup
            resp = client.post(url, json=payload)
            resp.raise_for_status()
    log.info("delivered %d message(s)", len(chunks))
