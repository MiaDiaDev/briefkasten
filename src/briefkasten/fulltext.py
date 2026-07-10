"""Fetch full article text so items are scored on content, not RSS stubs.

Untrusted content, same posture as feeds: it only ever enters fenced LLM
input. Fail soft per item — on any error the scorer falls back to the RSS
summary. Twitter items are skipped (the tweet already is the content).
"""

from __future__ import annotations

import logging

import httpx
import trafilatura

from .models import Item

log = logging.getLogger(__name__)
MAX_CHARS = 2500
HEADERS = {"User-Agent": "Mozilla/5.0 (briefkasten feed reader)"}


def enrich(items: list[Item]) -> None:
    with httpx.Client(timeout=10, follow_redirects=True, headers=HEADERS) as client:
        for it in items:
            if it.kind != "blog":
                continue
            try:
                resp = client.get(it.url)
                resp.raise_for_status()
                it.content = (trafilatura.extract(resp.text) or "")[:MAX_CHARS]
            except Exception as e:  # noqa: BLE001 — fall back to the RSS summary
                log.info("fulltext failed for %s: %s", it.url, e)
    n = sum(1 for it in items if it.content)
    log.info("fulltext extracted for %d of %d items", n, len(items))


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    item = Item(id="cli", title="", url=sys.argv[1], source="cli")
    enrich([item])
    print(item.content or "(no text extracted)")
