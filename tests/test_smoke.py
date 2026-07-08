"""Offline smoke tests: dedupe, scoring math, rendering, chunking."""

from briefkasten.brief import compose, render
from briefkasten.models import Item
from briefkasten.state import filter_new


def make_item(i: int, **kw) -> Item:
    defaults = dict(
        id=f"id{i}",
        title=f"Item {i}",
        url=f"https://example.com/{i}",
        source="Test",
        field_impact=5,
        work_relevance=5,
        personal_interest=5,
        summary="A test item.",
    )
    defaults.update(kw)
    return Item(**defaults)


def test_score_weighting():
    it = make_item(1, field_impact=10, work_relevance=0, personal_interest=0)
    assert it.score == 3.0  # 0.30 weight on field impact


def test_source_weight_multiplies():
    it = make_item(1, source_weight=1.2)
    assert it.score == 6.0  # 5.0 * 1.2


def test_filter_new():
    items = [make_item(1), make_item(2)]
    assert [i.id for i in filter_new(items, {"id1": "2026-01-01"})] == ["id2"]


def test_compose_splits_top_and_rest():
    items = [make_item(i, field_impact=i) for i in range(10)]
    brief = compose(items)
    assert len(brief.top) == 5
    assert brief.top[0].score >= brief.top[-1].score


def test_render_escapes_html_and_chunks():
    items = [make_item(1, title="<script>alert(1)</script>")]
    chunks = render(compose(items))
    assert all(len(c) <= 4000 for c in chunks)
    assert "<script>" not in chunks[0]


def test_render_empty_day():
    chunks = render(compose([]))
    assert "Quiet day" in chunks[0]
