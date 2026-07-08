# Briefkasten 📬

Personal AI news brief. Fetches your blogs + Twitter (via RSS bridges),
scores every new item with Claude against your interest profile, and drops
a ranked digest into Telegram every morning. Runs free on GitHub Actions.

## Setup

1. Create a Telegram bot via @BotFather → get `TELEGRAM_BOT_TOKEN`.
2. Message your bot once, then get your chat id:
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → `chat.id`.
3. Add repo secrets: `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
4. Tune `config/profile.md` (ranking rubric) and `config/sources.yaml` (feeds).
5. Test locally:

```bash
uv sync
cp .env.example .env   # fill in, then: set -a; source .env; set +a
uv run python -m briefkasten.main --dry-run
uv run pytest
```

6. Push to GitHub — the workflow runs daily at 06:00 UTC, or trigger it
   manually via the Actions tab (`workflow_dispatch`).

See `CLAUDE.md` for architecture and `ROADMAP.md` for what's next.
