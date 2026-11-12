"""Logic tests for radar/store.py. No network access."""

from datetime import date, timedelta

from radar import store


def test_upsert_new_topic():
    data = {"topics": []}
    topic = store.upsert_topic(data, "Model X", ["x", "github"], "必看",
                               today=date(2026, 11, 11))
    assert topic["first_seen"] == "2026-11-11"
    assert topic["sources"] == ["x", "github"]
    assert len(data["topics"]) == 1


def test_upsert_existing_keeps_first_seen_and_merges_sources():
    data = {"topics": []}
    store.upsert_topic(data, "Model X", ["x"], "苗头", today=date(2026, 11, 11))
    topic = store.upsert_topic(data, "Model X", ["reddit"], "关注",
                               today=date(2026, 11, 12))
    assert topic["first_seen"] == "2026-11-11"
    assert topic["last_seen"] == "2026-11-12"
    assert topic["sources"] == ["x", "reddit"]
    assert [h["grade"] for h in topic["history"]] == ["苗头", "关注"]


def test_review_due_after_14_days_only():
    data = {"topics": []}
    store.upsert_topic(data, "Old", ["x"], "关注", today=date(2026, 11, 1))
    store.upsert_topic(data, "New", ["x"], "关注", today=date(2026, 11, 10))
    due = store.due_for_review(data, today=date(2026, 11, 11) + timedelta(days=5))
    assert [t["name"] for t in due] == ["Old"]


def test_record_review_removes_from_due():
    data = {"topics": []}
    store.upsert_topic(data, "Old", ["x"], "关注", today=date(2026, 11, 1))
    store.record_review(data, "Old", "hit", today=date(2026, 11, 20))
    assert store.due_for_review(data, today=date(2026, 11, 21)) == []
