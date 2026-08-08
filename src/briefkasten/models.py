"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Item:
    """One news item flowing through the pipeline."""

    id: str  # normalized URL hash
    title: str
    url: str
    source: str
    kind: str = "blog"  # "blog" | "twitter" — twitter items skip full-text fetch
    author: str = ""  # groups sources of one person (blog + handle) for capping
    always_show: bool = False  # handpicked source: guaranteed at least "Also seen"
    source_weight: float = 1.0
    published: str = ""  # ISO 8601
    summary_raw: str = ""  # from the feed, untrusted
    content: str = ""  # full-text extract, untrusted; falls back to summary_raw

    # filled by scorer
    field_impact: int = 0
    work_relevance: int = 0
    personal_interest: int = 0
    summary: str = ""  # one sentence, model-written

    @property
    def score(self) -> float:
        weighted = (
            0.30 * self.field_impact
            + 0.45 * self.work_relevance
            + 0.25 * self.personal_interest
        )
        return round(weighted * self.source_weight, 2)


@dataclass
class Brief:
    date: str
    top: list[Item] = field(default_factory=list)
    rest: list[Item] = field(default_factory=list)
