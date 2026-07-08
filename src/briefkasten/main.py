"""Orchestrate one daily run: fetch → dedupe → score → compose → deliver."""

from __future__ import annotations

import argparse
import logging

from . import brief, deliver, fetch, score, state

log = logging.getLogger(__name__)


def run(dry_run: bool = False) -> None:
    items = fetch.fetch_all()
    seen = state.load_seen()
    new = state.filter_new(items, seen)
    log.info("%d new of %d fetched", len(new), len(items))

    if new:
        score.score_items(new)
    daily = brief.compose(new)
    chunks = brief.render(daily)

    if dry_run:
        for chunk in chunks:
            print("-" * 60)
            print(chunk)
    else:
        deliver.send(chunks)
        state.mark_seen(new, seen)  # only persist after successful delivery


def main() -> None:
    parser = argparse.ArgumentParser(prog="briefkasten")
    parser.add_argument("--dry-run", action="store_true", help="print, don't send")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
