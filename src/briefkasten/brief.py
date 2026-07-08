"""Compose the ranked brief as Telegram-ready HTML chunks."""

from __future__ import annotations

import html
from datetime import date

from .models import Brief, Item

TOP_N = 5
MIN_SCORE_FOR_REST = 3.0
TELEGRAM_LIMIT = 4000  # headroom under the 4096 hard limit


def compose(items: list[Item]) -> Brief:
    ranked = sorted(items, key=lambda it: it.score, reverse=True)
    top = ranked[:TOP_N]
    rest = [it for it in ranked[TOP_N:] if it.score >= MIN_SCORE_FOR_REST]
    return Brief(date=date.today().isoformat(), top=top, rest=rest)


def render(brief: Brief) -> list[str]:
    """Render to one or more HTML messages, each under the Telegram limit."""
    lines = [f"📬 <b>Briefkasten — {brief.date}</b>\n"]
    for i, it in enumerate(brief.top, 1):
        lines.append(
            f"{i}. <a href=\"{html.escape(it.url, quote=True)}\">"
            f"{html.escape(it.title)}</a> "
            f"<i>({it.score:.1f} · {html.escape(it.source)})</i>\n"
            f"{html.escape(it.summary)}\n"
        )
    if brief.rest:
        lines.append("<b>Also seen:</b>")
        lines.extend(
            f"· <a href=\"{html.escape(it.url, quote=True)}\">"
            f"{html.escape(it.title)}</a> <i>({it.score:.1f})</i>"
            for it in brief.rest
        )
    if not brief.top:
        lines.append("Quiet day — nothing new above the noise floor.")
    return _chunk(lines)


def _chunk(lines: list[str]) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > TELEGRAM_LIMIT:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
