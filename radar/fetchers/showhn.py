"""Show HN fetcher: launch posts on Hacker News (L1).

Show HN is where indie products announce themselves — a distinct
signal from the HN front page (news/discussion), so it is tracked
as its own source, via the same free Algolia API.
"""

from __future__ import annotations

from . import common

SOURCE = "show_hn"
LAYER = 1


def parse(payload: dict) -> list[dict]:
    """Pure parser for the Algolia response (unit-tested)."""
    items = []
    for hit in payload.get("hits", []):
        if not hit.get("title"):
            continue
        items.append({
            "source": SOURCE,
            "name": hit["title"],
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
            "metrics": {"points": hit.get("points"), "comments": hit.get("num_comments")},
            "detail": f"HN discussion: https://news.ycombinator.com/item?id={hit['objectID']}",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    try:
        payload = common.get_json(
            "https://hn.algolia.com/api/v1/search?tags=show_hn&hitsPerPage=30")
        return common.ok(SOURCE, LAYER, parse(payload))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
