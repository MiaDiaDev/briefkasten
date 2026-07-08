# Interest profile (scoring rubric)

This file is injected into the scoring prompt. Edit freely — it is the main
tuning knob for ranking.

## Axis 1 — Importance for the AI field (weight: 0.3)

High: frontier model releases, major capability or safety results, agent
architecture patterns, notable open-source releases, regulation with teeth
(EU AI Act enforcement), industry-shifting business moves.
Low: incremental benchmarks, hype threads, funding announcements without
technical substance.

## Axis 2 — Relevance to my work (weight: 0.45)

I am a solo AI engineer serving German/EU clients, specializing in OCR and
RAG pipelines.

High: OCR / document AI / layout understanding, RAG techniques and evals,
GDPR-compliant / EU-hosted / self-hosted inference (LiteLLM, Hetzner, EU
clouds), Claude/Anthropic ecosystem and Claude Code workflows, MCP,
agent tooling I could deploy for clients, vertical AI for insurance or
document-heavy industries, solo-founder B2B AI tooling.
Medium: LLM eval methodology, prompt engineering research, pricing changes
of major providers.

## Axis 3 — Personal interest (weight: 0.25)

Game dev with AI (Godot, procedural narrative), Taleb-style
risk/antifragility takes on AI, AI for indie hackers and nomads,
long-form technical writing of the Simon Willison sort, AI + creative
tools, occasionally: anything genuinely funny or weird in the space.

## Hard filters

- Score 0 on all axes: engagement-bait, crypto/AI token shills,
  "10 prompts that will change your life" listicles.
