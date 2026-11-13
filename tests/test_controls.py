"""Tests for the 0.4.0 user controls and the YAML config path."""

import types
from datetime import datetime, timedelta, timezone

from radar import config as config_mod
from radar import scan as scan_mod
from radar import yamlmini
from radar.__main__ import auto_edition

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def _item(name, detail="", published=None, source="test"):
    metrics = {}
    if published:
        metrics["published"] = published
    return {"source": source, "name": name, "url": "https://example.com",
            "metrics": metrics, "detail": detail}


def test_yaml_parsers_agree_on_example():
    with open("config.example.yaml", encoding="utf-8") as fh:
        text = fh.read()
    assert config_mod.parse_yaml(text) == yamlmini.loads(text)


def test_yamlmini_subset():
    doc = """
# comment
a: 1
b:
  c: hello
  d: [x, y]
list:
  - name: one
    url: "https://example.com/1"
  - name: two
    url: 'https://example.com/2'
flag: true
empty: []
nothing: null
"""
    parsed = yamlmini.loads(doc)
    assert parsed["a"] == 1 and parsed["b"]["d"] == ["x", "y"]
    assert parsed["list"][1]["name"] == "two"
    assert parsed["flag"] is True and parsed["empty"] == [] and parsed["nothing"] is None


def test_item_time_formats():
    iso = _item("x", published="2026-11-13T10:00:00Z")
    assert scan_mod.item_time(iso) == datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
    rfc = _item("x", published="13 Nov 2026 00:36 +0000")
    assert scan_mod.item_time(rfc).hour == 0
    assert scan_mod.item_time(_item("x")) is None


def test_controls_mute_boost_alert_topics_age():
    fresh = (NOW - timedelta(hours=2)).isoformat()
    stale = (NOW - timedelta(hours=100)).isoformat()
    results = [{"source": "test", "layer": 1, "status": "ok", "note": "", "items": [
        _item("Free giveaway now"),                       # muted
        _item("MCP server released", published=fresh),     # boost + topic
        _item("Gemini 9 launches", published=fresh),       # alert
        _item("Old news", published=stale),                # stale
        _item("Undated thing"),                            # kept (no timestamp)
    ]}]
    config = {"keywords": {"mute": ["giveaway"], "boost": ["mcp"],
                           "alert": ["gemini"]},
              "topics": {"AI Agents": 5},
              "filters": {"max_age_hours": 48}}
    # give the boost item a topic hit via its detail
    results[0]["items"][1]["detail"] = "an AI Agents tool"
    stats, alerts = scan_mod.apply_controls(results, config, NOW)
    names = [i["name"] for i in results[0]["items"]]
    assert names == ["MCP server released", "Gemini 9 launches", "Undated thing"]
    assert stats == {"muted": 1, "stale": 1, "boost_tagged": 1, "alert_tagged": 1}
    assert alerts[0]["keywords"] == ["gemini"]
    kept = {i["name"]: i for i in results[0]["items"]}
    assert kept["MCP server released"]["keyword_hits"]["boost"] == ["mcp"]
    assert kept["MCP server released"]["topic_hits"] == {"AI Agents": 5}


def test_topic_weights_legacy_list():
    config = {"grading": {"relevance_topics": ["A", "B"]}}
    assert scan_mod.topic_weights(config) == {"A": 1, "B": 1}
    config2 = {"topics": {"A": 5}}
    assert scan_mod.topic_weights(config2) == {"A": 5}


def _fake_fetcher(source, items):
    return types.SimpleNamespace(
        SOURCE=source, LAYER=1,
        fetch=lambda config, now=None: {"source": source, "layer": 1,
                                        "status": "ok", "items": items, "note": ""})


def test_run_scan_disabled_and_max_items(tmp_out="state"):
    many = [_item(f"item {i}") for i in range(5)]
    fake_on = _fake_fetcher("fakeon", many)
    fake_off = _fake_fetcher("fakeoff", many)
    original = scan_mod.FETCHERS
    scan_mod.FETCHERS = [fake_on, fake_off]
    try:
        config = {"sources": {"fakeoff": {"enabled": False},
                              "fakeon": {"max_items": 2}}}
        report = scan_mod.run_scan("morning", config, now=NOW, out_dir="/tmp")
    finally:
        scan_mod.FETCHERS = original
    by_source = {r["source"]: r for r in report["sources"]}
    assert by_source["fakeoff"]["status"] == "disabled"
    assert report["disabled"] == ["fakeoff"]
    assert len(by_source["fakeon"]["items"]) == 2
    assert "max_items" in by_source["fakeon"]["note"]


def test_auto_edition():
    assert auto_edition(datetime(2026, 11, 13, 6, 0)) == "morning"
    assert auto_edition(datetime(2026, 11, 13, 18, 0)) == "evening"
