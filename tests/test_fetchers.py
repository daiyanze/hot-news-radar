"""Parser tests for the fetch layer. No network access: every test
feeds a small recorded-shaped fixture into a pure parse function."""

from datetime import datetime, timezone

from radar import scan as scan_mod
from radar.fetchers import (appstore, arxiv, bluesky, civitai, common,
                            dailypapers, devto, github, googlenews, hackernews,
                            hfspaces, huggingface, lobsters, mastodon,
                            openrouter, producthunt, reddit, showhn, sitemaps,
                            wikipedia)

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


def test_parse_feed_rss_and_atom():
    rss = ('<rss><channel><item><title>Launch</title>'
           '<link>https://example.com/a</link><pubDate>Thu, 13 Nov 2026</pubDate>'
           '</item></channel></rss>')
    items = common.parse_feed(rss, "official_blogs", "Example")
    assert items[0]["name"] == "Launch" and items[0]["metrics"]["outlet"] == "Example"
    atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Post</title>'
            '<link rel="alternate" href="https://example.com/b"/>'
            '<published>2026-11-13T00:00:00Z</published></entry></feed>')
    items = common.parse_feed(atom, "tech_media", "Atom Blog")
    assert items[0]["url"] == "https://example.com/b"


def test_producthunt_feed_parse():
    atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>NewTool</title>'
            '<link href="https://www.producthunt.com/posts/newtool"/></entry></feed>')
    items = producthunt.parse_feed(atom)
    assert items[0]["name"] == "NewTool"


def test_arxiv_parse():
    xml = ('<feed xmlns="http://www.w3.org/2005/Atom" '
           'xmlns:arxiv="http://arxiv.org/schemas/atom"><entry>'
           '<id>http://arxiv.org/abs/2611.00001v1</id>'
           '<title>A  New\n Method</title><published>2026-11-12T00:00:00Z</published>'
           '<summary>We propose things.</summary>'
           '<arxiv:primary_category term="cs.CL"/>'
           '<author><name>A</name></author></entry></feed>')
    items = arxiv.parse(xml)
    assert items[0]["name"] == "A New Method"
    assert items[0]["metrics"]["category"] == "cs.CL"


def test_openrouter_newest_first_and_new_flag():
    import time
    recent = int((NOW.timestamp())) - 2 * 86400
    old = int((NOW.timestamp())) - 200 * 86400
    payload = {"data": [
        {"id": "acme/old", "name": "Old", "created": old},
        {"id": "acme/new", "name": "New", "created": recent, "context_length": 128000}]}
    items = openrouter.parse(payload, NOW)
    assert items[0]["metrics"]["model_id"] == "acme/new"
    assert items[0]["metrics"]["is_new"] is True
    assert items[1]["metrics"]["is_new"] is False


def test_hfspaces_new_face():
    payload = [{"id": "acme/demo", "likes": 5, "trendingScore": 10, "sdk": "gradio",
                "createdAt": "2026-11-10T00:00:00.000Z"}]
    items = hfspaces.parse(payload, NOW)
    assert items[0]["url"] == "https://huggingface.co/spaces/acme/demo"
    assert items[0]["metrics"]["new_face"] is True


def test_showhn_parse():
    payload = {"hits": [{"title": "Show HN: Thing", "url": None, "points": 12,
                         "num_comments": 3, "objectID": "99"}]}
    items = showhn.parse(payload)
    assert items[0]["url"] == "https://news.ycombinator.com/item?id=99"


def test_devto_and_lobsters_parse():
    dev = devto.parse([{"title": "Post", "url": "https://dev.to/x",
                        "public_reactions_count": 40, "comments_count": 5,
                        "reading_time_minutes": 3, "description": "d"}])
    assert dev[0]["metrics"]["reactions"] == 40
    lob = lobsters.parse([{"title": "Story", "url": "https://example.com",
                           "comments_url": "https://lobste.rs/s/abc", "score": 30,
                           "comment_count": 9, "tags": ["ai"]}])
    assert lob[0]["metrics"]["score"] == 30


def test_mastodon_parse():
    links = mastodon.parse_links([{"title": "Big Story", "url": "https://x.example",
                                   "provider_name": "Outlet", "description": "d",
                                   "history": [{"accounts": "42", "uses": "50"}]}])
    assert links[0]["metrics"]["accounts_today"] == 42
    tags = mastodon.parse_tags([{"name": "ai", "url": "https://m/tags/ai",
                                 "history": [{"accounts": "7"}]}])
    assert tags[0]["name"] == "#ai"


def test_civitai_parse():
    payload = {"items": [{"id": 7, "name": "Model X", "type": "Checkpoint",
                          "stats": {"downloadCount": 100, "thumbsUpCount": 9},
                          "modelVersions": [{"baseModel": "Flux"}]}]}
    items = civitai.parse(payload)
    assert items[0]["url"] == "https://civitai.com/models/7"
    assert items[0]["metrics"]["base_models"] == ["Flux"]


def test_appstore_parse_ranks():
    payload = {"feed": {"results": [
        {"name": "AppA", "url": "https://apps.apple.com/a", "artistName": "A Inc",
         "genres": [{"name": "Productivity"}]},
        {"name": "AppB", "url": "https://apps.apple.com/b", "artistName": "B Inc",
         "genres": []}]}}
    items = appstore.parse(payload, "top-grossing")
    assert items[0]["metrics"]["rank"] == 1 and items[1]["metrics"]["rank"] == 2


def test_sitemaps_urlset_filters_and_sorts():
    xml = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           '<url><loc>https://www.futurepedia.io/tool/new-thing</loc>'
           '<lastmod>2026-11-11T00:00:00.000Z</lastmod></url>'
           '<url><loc>https://www.futurepedia.io/tool/old-thing</loc>'
           '<lastmod>2026-01-01T00:00:00.000Z</lastmod></url>'
           '<url><loc>https://www.futurepedia.io/ai-tools</loc></url></urlset>')
    site = {"name": "futurepedia", "pattern": r"/tool/([^/]+)$", "max_age_days": 7}
    items = sitemaps.parse_urlset(xml, site, NOW)
    assert len(items) == 1 and items[0]["name"] == "new thing"


def test_sitemaps_index_picks_highest_shard():
    xml = ('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           '<sitemap><loc>https://www.toolify.ai/sitemap_tools_2.xml</loc></sitemap>'
           '<sitemap><loc>https://www.toolify.ai/sitemap_tools_10.xml</loc></sitemap>'
           '<sitemap><loc>https://www.toolify.ai/sitemap_index_1.xml</loc></sitemap>'
           '</sitemapindex>')
    shards = sitemaps.parse_index(xml, r"sitemap_tools_(\d+)\.xml$")
    assert shards[-1] == "https://www.toolify.ai/sitemap_tools_10.xml"


def test_dailypapers_parse():
    payload = [{"title": "T", "numComments": 4,
                "paper": {"id": "2611.08219", "title": "Agent Scaling",
                          "summary": "We scale.", "upvotes": 42,
                          "authors": [{"name": "A"}, {"name": "B"}],
                          "githubRepo": "acme/agent"}}]
    items = dailypapers.parse(payload)
    assert items[0]["url"] == "https://huggingface.co/papers/2611.08219"
    assert items[0]["metrics"]["upvotes"] == 42


def test_bluesky_parse_uses_description_as_name():
    xml = ('<rss><channel><item>'
           '<link>https://bsky.app/profile/x/post/1</link>'
           '<description>Big news: a new model dropped</description>'
           '<pubDate>13 Nov 2026 00:36 +0000</pubDate>'
           '</item></channel></rss>')
    items = bluesky.parse(xml, "x")
    assert items[0]["name"] == "Big news: a new model dropped"
    assert items[0]["metrics"]["account"] == "x"


def test_wikipedia_parse_skips_meta_pages():
    payload = {"items": [{"articles": [
        {"article": "Main_Page", "views": 4000000, "rank": 1},
        {"article": "Jensen_Huang", "views": 1000000, "rank": 2},
        {"article": "Special:Search", "views": 900000, "rank": 3},
        {"article": "Some_Event", "views": 500000, "rank": 4}]}]}
    items = wikipedia.parse(payload)
    assert [i["name"] for i in items] == ["Jensen Huang", "Some Event"]
    assert items[0]["metrics"]["views"] == 1000000


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
