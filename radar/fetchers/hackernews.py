"""Hacker News fetcher via the Algolia front-page API (one request)."""

from __future__ import annotations

from . import common

SOURCE = "hackernews"
LAYER = 1


def parse(payload: dict) -> list[dict]:
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
        payload = common.get_json("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30")
        return common.ok(SOURCE, LAYER, parse(payload))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
