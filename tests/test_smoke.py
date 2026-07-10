"""Offline smoke tests: dedupe, scoring math, rendering, chunking."""

import json
from datetime import date

from briefkasten.brief import compose, render
from briefkasten.deepdive import load_week, sanitize
from briefkasten.deliver import keyboard
from briefkasten.feedback import parse_updates, resolve
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
    assert len(brief.top) == 7
    assert brief.top[0].score >= brief.top[-1].score


def test_render_collapses_long_titles_to_summary():
    tweet = make_item(1, title="x" * 300, summary="One concise sentence.")
    out = render(compose([tweet]))[0]
    assert "One concise sentence.</a>" in out  # summary became the linked headline
    assert "xxx" not in out
    assert out.count("One concise sentence.") == 1  # no duplicated summary line


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
    assert kb["keyboard"] == [["1 👍", "1 👎", "1 🔖"], ["2 👍", "2 👎", "2 🔖"]]
    assert keyboard([]) is None


def test_parse_updates_routes_taps_and_card_replies():
    updates = [
        {"update_id": 10, "message": {"from": {"id": 617}, "date": 0, "text": "hi"}},
        {"update_id": 11, "message": {"from": {"id": 999}, "date": 0, "text": "1 👍"}},
        {"update_id": 12, "message": {"from": {"id": 617}, "date": 0, "text": "6teen 👍👍"}},
        {"update_id": 13, "message": {"from": {"id": 617}, "date": 86400, "text": "2🔖"}},
    ]
    taps, texts, max_id = parse_updates(updates, "617")
    assert taps == [{"msg_date": "1970-01-02", "rank": 2, "action": "save"}]
    # owner non-feedback texts become card replies; foreign chat dropped entirely
    assert [t["text"] for t in texts] == ["hi", "6teen 👍👍"]
    assert max_id == 13


def test_card_deck_rotation_and_pool_no_repeat(tmp_path):
    from briefkasten import card

    cfg = {
        "rotation": {1: "spanish", 6: "review"},
        "decks": {"necro": {"pool": str(tmp_path / "pool.json")}},
    }
    assert card.pick_deck(1, cfg) == "spanish"
    assert card.pick_deck(7, cfg) is None  # Sunday off

    pool = [{"id": "a", "title": "A", "url": "u", "folder": "f"},
            {"id": "b", "title": "B", "url": "u", "folder": "f"}]
    (tmp_path / "pool.json").write_text(json.dumps(pool))
    state = {"used_pool_ids": []}
    picks = set()
    for day in (date(2026, 7, 14), date(2026, 7, 21)):
        picks.add(card.build_task("necro", cfg, state, day)["bookmark"]["id"])
    assert picks == {"a", "b"}  # no repeat while fresh entries remain


def test_card_replies_since_and_streak_semantics():
    from briefkasten.card import replies_since

    rows = [{"date": "2026-07-09", "text": "old"}, {"date": "2026-07-10", "text": "⏭ skip"}]
    since = replies_since(rows, "2026-07-10")
    assert since == [{"date": "2026-07-10", "text": "⏭ skip"}]
    assert [r for r in since if r["text"].strip() != "⏭ skip"] == []  # skip breaks streak


def test_resolve_maps_rank_to_latest_prior_brief():
    history = [
        {"date": "2026-07-09", "rank": 2, "id": "old2"},
        {"date": "2026-07-10", "rank": 2, "id": "new2"},
        {"date": "2026-07-10", "rank": None, "id": "unranked"},
    ]
    taps = [
        {"msg_date": "2026-07-10", "rank": 2, "action": "up"},  # latest brief wins
        {"msg_date": "2026-07-09", "rank": 2, "action": "save"},  # older msg -> older brief
        {"msg_date": "2026-07-10", "rank": 5, "action": "up"},  # no rank 5 -> dropped
        {"msg_date": "2026-07-01", "rank": 1, "action": "up"},  # before any brief -> dropped
    ]
    assert [(r["action"], r["item_id"]) for r in resolve(taps, history)] == [
        ("up", "new2"),
        ("save", "old2"),
    ]


def test_load_week_windows_seven_days():
    rows = [{"date": "2026-07-04"}, {"date": "2026-07-03"}, {"date": "2026-07-10"}]
    assert load_week(rows, date(2026, 7, 10)) == [
        {"date": "2026-07-04"},
        {"date": "2026-07-10"},
    ]


def test_sanitize_allows_only_b_and_i():
    out = sanitize('<b>Theme</b> <i>x</i> <a href="https://evil.example">link</a> 1<2')
    assert "<b>Theme</b>" in out and "<i>x</i>" in out
    assert "<a" not in out and "1&lt;2" in out


def test_enrich_skips_twitter_and_fails_soft(monkeypatch):
    from briefkasten import fulltext

    class FakeResp:
        text = "<html><body><article><p>" + "Real article text. " * 30 + "</p></article></body></html>"

        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def get(self, url):
            if "dead" in url:
                raise OSError("connection refused")
            return FakeResp()

    monkeypatch.setattr(fulltext.httpx, "Client", FakeClient)
    blog = make_item(1, url="https://example.com/post")
    tweet = make_item(2, kind="twitter")
    dead = make_item(3, url="https://dead.example.com/x", summary_raw="rss stub")
    fulltext.enrich([blog, tweet, dead])
    assert "Real article text." in blog.content
    assert len(blog.content) <= fulltext.MAX_CHARS
    assert tweet.content == ""  # skipped
    assert dead.content == ""  # failed soft; scorer falls back to summary_raw


def test_append_history_writes_and_prunes(tmp_path):
    path = tmp_path / "history.jsonl"
    path.write_text(json.dumps({"date": "2020-01-01", "id": "old"}) + "\n")
    append_history("2026-07-09", [make_item(1)], ranks={"id1": 3}, path=path)
    rows = [json.loads(ln) for ln in path.read_text().splitlines()]
    assert [r["id"] for r in rows] == ["id1"]  # ancient row pruned
    assert rows[0]["score"] == 5.0
    assert rows[0]["rank"] == 3
