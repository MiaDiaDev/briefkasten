"""Compose the ranked brief as Telegram-ready HTML chunks."""

from __future__ import annotations

import html
from datetime import date

from .models import Brief, Item

TOP_N = 7
MAX_TOP_PER_SOURCE = 2  # prolific single authors can't own the brief
MIN_SCORE_FOR_REST = 2.5
TELEGRAM_LIMIT = 4000  # headroom under the 4096 hard limit
MAX_HEADLINE = 90  # longer titles (usually tweets) collapse to the summary


def compose(items: list[Item]) -> Brief:
    ranked = sorted(items, key=lambda it: it.score, reverse=True)
    top: list[Item] = []
    rest: list[Item] = []
    per_source: dict[str, int] = {}
    for it in ranked:
        if len(top) < TOP_N and per_source.get(it.source, 0) < MAX_TOP_PER_SOURCE:
            top.append(it)
            per_source[it.source] = per_source.get(it.source, 0) + 1
        elif it.score >= MIN_SCORE_FOR_REST:
            rest.append(it)
    return Brief(date=date.today().isoformat(), top=top, rest=rest)


def _headline(it: Item) -> str:
    """One concise line: the title, or the summary sentence when the title
    is a wall of text (tweets); truncate as a last resort."""
    if len(it.title) <= MAX_HEADLINE:
        return it.title
    return it.summary or it.title[: MAX_HEADLINE - 1] + "…"


def render(brief: Brief) -> list[str]:
    """Render to one or more HTML messages, each under the Telegram limit."""
    lines = [f"📬 <b>Briefkasten — {brief.date}</b>\n"]
    for i, it in enumerate(brief.top, 1):
        headline = _headline(it)
        line = (
            f"{i}. <a href=\"{html.escape(it.url, quote=True)}\">"
            f"{html.escape(headline)}</a> "
            f"<i>({it.score:.1f} · {html.escape(it.source)})</i>\n"
        )
        if headline == it.title and it.summary:  # summary not already the headline
            line += f"{html.escape(it.summary)}\n"
        lines.append(line)
    if brief.rest:
        lines.append("<b>Also seen:</b>")
        lines.extend(
            f"· <a href=\"{html.escape(it.url, quote=True)}\">"
            f"{html.escape(_headline(it))}</a> <i>({it.score:.1f})</i>"
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
