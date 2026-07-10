# Roadmap

## Phase 1 — Daily ranked brief (current)

Goal: one reliable Telegram message every morning.

- [ ] Fetch all sources from `config/sources.yaml` (RSS + Twitter bridges)
- [ ] Dedupe against `data/seen.json` (URL-normalized + title fuzzy match)
- [ ] Batch-score new items with Claude against `config/profile.md`
      → per-item: `field_impact`, `work_relevance`, `personal_interest`
      (0–10 each), one-sentence summary, weighted total
- [ ] Compose brief: 🔥 top 5 with summaries, then a compact "also seen" list
- [ ] Deliver via Telegram Bot API, chunked under 4096 chars
- [ ] GitHub Actions cron (06:00 UTC ≈ 07:00 CET), commit state back
- [ ] `--dry-run` flag for local testing

Definition of done: 7 consecutive mornings without manual intervention.

## Phase 2 — Feedback loop & better signal

- [ ] Telegram inline buttons (👍 / 👎 / 🔖 save) — needs a webhook or a
      getUpdates poll step at the start of each daily run (serverless-friendly)
- [ ] Feedback adjusts `profile.md` weights (Claude proposes edits, owner approves via PR)
- [ ] Weekly deep-dive: Sunday long-form synthesis of the week's themes
- [ ] Full-text fetch for top items (not just RSS summaries) before scoring
- [ ] Source quality stats: which feeds produce high scorers, which are noise

## Phase 3 — Proactive assistant ("Sen-lite")

Guiding constraint: Simon Willison's lethal trifecta. Once the system touches
private data (calendar, email) AND reads untrusted content AND can write
externally, compartmentalize:

- Main agent: reads everything, writes nothing external
- Ephemeral subagents: single-purpose external actions, minimal context
- Credentials: never in agent context; broker/proxy pattern (arbiter grants
  placeholder tokens, proxy rewrites at the network edge)

Candidate features:

- [ ] "You should know about X" pushes outside the daily schedule (breaking
      items above a score threshold)
- [ ] Proactive nudges: hints on relevant events/opportunities and occasional
      pushes in a good direction — accountability toward stated goals, not a
      fixed "conference radar" (complements Mastmate, which owns daily
      commitment tracking)
- [ ] Research tasks on demand ("summarize everything on topic Y this month")
- [ ] Cross-pollination with Trailmix: high-scoring trends → product idea seeds
- [ ] Migration off GitHub Actions to a small VPS if/when interactivity
      demands an always-on process (same box as Mastmate is plausible)

## Non-goals (for now)

- No email triage, no calendar access, no write access to anything but
  Telegram — keeps v1/v2 structurally outside the trifecta.
- No vector DB / embeddings until dedupe or "related items" actually needs it.
