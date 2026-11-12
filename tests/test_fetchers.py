"""Parser tests for the fetch layer. No network access: every test
feeds a small recorded-shaped fixture into a pure parse function."""

from datetime import datetime, timezone

from radar import scan as scan_mod
from radar.fetchers import github, googlenews, hackernews, huggingface, reddit

NOW = datetime(2026, 11, 12, tzinfo=timezone.utc)


def test_github_breakout_math():
    payload = {"items": [{
        "full_name": "acme/fastthing", "html_url": "https://github.com/acme/fastthing",
        "stargazers_count": 3000, "created_at": "2026-11-02T00:00:00Z",
        "description": "fast thing"}]}
    items = github.parse_search(payload, NOW, {"max_age_days": 14, "min_stars_per_day": 200})
    assert items[0]["metrics"]["age_days"] == 10
    assert items[0]["metrics"]["stars_per_day"] == 300.0
    assert items[0]["metrics"]["breakout"] is True


def test_github_old_repo_not_breakout():
    payload = {"items": [{
        "full_name": "acme/old", "html_url": "https://github.com/acme/old",
        "stargazers_count": 9000, "created_at": "2025-01-01T00:00:00Z",
        "description": ""}]}
    items = github.parse_search(payload, NOW, {})
    assert items[0]["metrics"]["breakout"] is False


def test_github_trending_parse():
    html = ('<article class="Box-row"><h2><a href="/meta/astryx">x</a></h2>'
            '<a href="/meta/astryx/stargazers">23,622</a>'
            '<span>3,108 stars today</span></article>')
    items = github.parse_trending(html)
    assert items[0]["name"] == "meta/astryx"
    assert items[0]["metrics"]["stars_today"] == 3108
    assert items[0]["metrics"]["stars"] == 23622


def test_hn_parse_skips_stories_without_title():
    payload = {"hits": [
        {"title": "Big Story", "url": "https://example.com", "points": 500,
         "num_comments": 200, "objectID": "1"},
        {"title": None, "url": None, "points": 1, "num_comments": 0, "objectID": "2"}]}
    items = hackernews.parse(payload)
    assert len(items) == 1 and items[0]["metrics"]["points"] == 500


def test_hf_new_face_flag():
    payload = [{"id": "acme/new-model", "likes": 10, "downloads": 100,
                "createdAt": "2026-11-10T00:00:00.000Z"},
               {"id": "acme/old-model", "likes": 99, "downloads": 999,
                "createdAt": "2025-01-01T00:00:00.000Z"}]
    items = huggingface.parse(payload, NOW)
    assert items[0]["metrics"]["new_face"] is True
    assert items[1]["metrics"]["new_face"] is False


def test_reddit_parse_skips_stickied():
    payload = {"data": {"children": [
        {"data": {"title": "Pinned", "permalink": "/r/x/1", "score": 1,
                  "num_comments": 0, "stickied": True}},
        {"data": {"title": "Real Post", "permalink": "/r/x/2", "score": 42,
                  "num_comments": 7, "stickied": False}}]}}
    items = reddit.parse(payload, "x")
    assert len(items) == 1 and items[0]["name"] == "Real Post"


def test_reddit_rss_parse():
    xml = ('<feed xmlns="http://www.w3.org/2005/Atom">'
           '<entry><title>Cool local model</title>'
           '<link href="https://www.reddit.com/r/LocalLLaMA/comments/abc"/></entry></feed>')
    items = reddit.parse_rss(xml, "LocalLLaMA")
    assert items[0]["name"] == "Cool local model"
    assert items[0]["metrics"]["via"] == "rss"


def test_googlenews_parse():
    xml = ('<rss><channel><item><title>Story - Outlet</title>'
           '<link>https://example.com/s</link><pubDate>Wed, 12 Nov 2026</pubDate>'
           '<source url="https://example.com">Outlet</source></item></channel></rss>')
    items = googlenews.parse(xml)
    assert items[0]["name"] == "Story - Outlet"
    assert items[0]["metrics"]["outlet"] == "Outlet"


def test_resonance_needs_two_sources():
    results = [
        {"source": "github", "items": [{"source": "github", "name": "acme/zephyr",
                                        "url": "u1"}]},
        {"source": "hackernews", "items": [{"source": "hackernews", "name": "Zephyr launches",
                                            "url": "u2"},
                                           {"source": "hackernews", "name": "Unrelated thing",
                                            "url": "u3"}]},
    ]
    groups = scan_mod.resonance_groups(results)
    assert len(groups) == 1 and groups[0]["token"] == "zephyr"
