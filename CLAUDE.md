# Briefkasten — personal AI news brief

Daily pipeline that collects AI news from RSS feeds (blogs + Twitter/X via RSS
bridges), deduplicates, scores each item with Claude against a personal interest
profile, and delivers a ranked brief to Telegram. Runs on GitHub Actions cron —
no server, state committed back to the repo.

## Owner context

- Solo AI engineer, German/EU clients, OCR + RAG pipelines. GDPR-aware.
- Ranking axes (see `config/profile.md`): (1) importance for the AI field,
  (2) relevance to the owner's work, (3) personal interest.
- Long-term vision: evolve from a passive digest into a proactive
  assistant (see ROADMAP.md), following a compartmentalized agent
  architecture (main agent has no external write access; ephemeral
  subagents do; credentials never touch agents directly).

## Architecture (v1)

```
fetch (feedparser) → dedupe (data/seen.json) → score (Claude API, strict JSON)
→ brief (compose Markdown) → deliver (Telegram Bot API sendMessage)
```

- `src/briefkasten/fetch.py`   — pull feeds from `config/sources.yaml`
- `src/briefkasten/state.py`   — seen-item store (JSON in repo, committed by CI)
- `src/briefkasten/score.py`   — batch-score items with Claude; strict JSON out
- `src/briefkasten/brief.py`   — compose the ranked digest
- `src/briefkasten/deliver.py` — Telegram sendMessage (HTML parse mode)
- `src/briefkasten/main.py`    — orchestrates the run
- `.github/workflows/daily-brief.yml` — cron trigger + state commit-back

## Key decisions & constraints

- **Model:** `claude-haiku-4-5` for scoring (cheap, daily volume). One batched
  call per ~20 items, not one call per item.
- **Feed content is untrusted input.** It goes into LLM prompts, so treat it as
  potential prompt injection: the scorer's output is constrained to a JSON
  schema of numeric scores + one summary sentence; validate before use; the
  pipeline never executes actions derived from feed content. v1 is
  read-fetch/write-Telegram only — no lethal trifecta (no private data, no
  agent-driven external comms).
- **State in repo:** `data/seen.json` is committed back by the workflow with
  `[skip ci]`. Keep it capped (prune entries older than 30 days).
- **Twitter via RSS bridges** (RSSHub / openrss.org / self-hosted Nitter).
  Bridges are flaky — every source in `sources.yaml` is just a URL, so a dead
  bridge is a one-line config swap. Fetch failures must degrade gracefully
  (log + skip, never crash the run).
- **Secrets:** `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  live in GitHub Actions secrets. Never commit them; `.env` for local runs.
- **Telegram limits:** 4096 chars/message. Split the brief into chunks; top
  items first. Use HTML parse mode (MarkdownV2 escaping is a footgun).

## Conventions

- Python 3.12, `uv` for deps, `ruff` for lint/format, `pytest` for tests.
- Type hints everywhere; dataclasses for models; no heavy frameworks.
- Every module runnable standalone for debugging
  (`python -m briefkasten.fetch` prints fetched items, etc.).
- Fail soft: a broken feed or a failed score must never kill the daily brief.

## Commands

```bash
uv sync                          # install
uv run python -m briefkasten.main --dry-run   # full run, print instead of send
uv run pytest                    # tests
uv run ruff check --fix .        # lint
```
