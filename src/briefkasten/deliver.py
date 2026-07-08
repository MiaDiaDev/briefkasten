"""Deliver the brief via the Telegram Bot API (outbound HTTPS only)."""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)


def send(chunks: list[str]) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with httpx.Client(timeout=20) as client:
        for chunk in chunks:
            resp = client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            resp.raise_for_status()
    log.info("delivered %d message(s)", len(chunks))
