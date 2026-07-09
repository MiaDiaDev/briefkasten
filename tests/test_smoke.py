"""Offline smoke tests: dedupe, scoring math, rendering, chunking."""

import json

from briefkasten.brief import compose, render
from briefkasten.deliver import keyboard
from briefkasten.feedback import parse_updates
from briefkasten.models import Item
from briefkasten.state import append_history, dedupe, filter_new


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


def test_dedupe_fuzzy_titles_keeps_highest_weight():
    a = make_item(1, title="sqlite-utils 4.0 released", source_weight=1.0)
    b = make_item(2, title="Sqlite-utils 4.0 released!", source_weight=1.2)
    assert dedupe([a, b]) == [b]


def test_dedupe_tweet_linking_to_blog_keeps_blog():
    blog = make_item(
        1, title="sqlite-utils 4.0", url="https://simonwillison.net/2026/sqlite-utils-4"
    )
    tweet = make_item(
        2,
        title="Big release day for my CLI tools",
        source_weight=1.5,  # weight alone must not beat the linked-to blog post
        summary_raw='So: <a href="https://simonwillison.net/2026/sqlite-utils-4/">new post</a>',
    )
    assert dedupe([blog, tweet]) == [blog]


def test_dedupe_keeps_distinct_items():
    items = [
        make_item(1, title="Anthropic ships Fable 5"),
        make_item(2, title="EU AI Act guidance updated"),
    ]
    assert dedupe(items) == items


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


def test_keyboard_one_row_per_item():
    kb = keyboard([make_item(1), make_item(2)])
    assert len(kb["inline_keyboard"]) == 2
    assert kb["inline_keyboard"][0][0]["callback_data"] == "up:id1"
    assert kb["inline_keyboard"][1][2]["callback_data"] == "save:id2"
    assert keyboard([]) is None


def test_parse_updates_filters_foreign_and_malformed():
    updates = [
        {"update_id": 10, "message": {"text": "hi"}},  # not a button press
        {
            "update_id": 11,
            "callback_query": {"from": {"id": 999}, "data": "up:id1"},  # wrong chat
        },
        {
            "update_id": 12,
            "callback_query": {"from": {"id": 617}, "data": "drop table;--"},
        },
        {
            "update_id": 13,
            "callback_query": {"from": {"id": 617}, "data": "save:id7"},
        },
    ]
    rows, max_id = parse_updates(updates, "617")
    assert [(r["action"], r["item_id"]) for r in rows] == [("save", "id7")]
    assert max_id == 13


def test_append_history_writes_and_prunes(tmp_path):
    path = tmp_path / "history.jsonl"
    path.write_text(json.dumps({"date": "2020-01-01", "id": "old"}) + "\n")
    append_history("2026-07-09", [make_item(1)], path=path)
    rows = [json.loads(ln) for ln in path.read_text().splitlines()]
    assert [r["id"] for r in rows] == ["id1"]  # ancient row pruned
    assert rows[0]["score"] == 5.0
