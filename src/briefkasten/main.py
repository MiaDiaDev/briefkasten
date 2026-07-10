"""Orchestrate one daily run: fetch → dedupe → score → compose → deliver."""

from __future__ import annotations

import argparse
import logging

from . import brief, deliver, feedback, fetch, score, state

log = logging.getLogger(__name__)


def run(dry_run: bool = False) -> None:
    if not dry_run:  # dry runs must not consume pending button presses
        try:
            harvested = feedback.poll()
            if harvested:
                log.info("harvested %d feedback event(s)", len(harvested))
        except Exception:  # noqa: BLE001 — feedback must never block the brief
            log.exception("feedback poll failed, continuing")

    items = fetch.fetch_all()
    seen = state.load_seen()
    new = state.filter_new(items, seen)
    unique = state.dedupe(new)
    log.info("%d unique of %d new (%d fetched)", len(unique), len(new), len(items))

    if unique:
        score.score_items(unique)
    daily = brief.compose(unique)
    chunks = brief.render(daily)

    if dry_run:
        for chunk in chunks:
            print("-" * 60)
            print(chunk)
    else:
        deliver.send(chunks, deliver.keyboard(daily.top))
        # only persist after successful delivery; mark all new ids (including
        # collapsed duplicates) so a dropped tweet can't resurface tomorrow
        state.mark_seen(new, seen)
        ranks = {it.id: n for n, it in enumerate(daily.top, 1)}
        state.append_history(daily.date, unique, ranks)


def main() -> None:
    parser = argparse.ArgumentParser(prog="briefkasten")
    parser.add_argument("--dry-run", action="store_true", help="print, don't send")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # urls contain the bot token
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
