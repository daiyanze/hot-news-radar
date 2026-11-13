"""Lobsters fetcher: hottest stories on lobste.rs (L2).

A small, high-signal developer community with public JSON and no
key. It often surfaces the same stories as HN hours later with
sharper commentary — a good fermentation cross-check.
"""

from __future__ import annotations

from . import common

SOURCE = "lobsters"
LAYER = 2


def parse(payload: list) -> list[dict]:
    """Pure parser for the Lobsters hottest response (unit-tested)."""
    items = []
    for story in payload:
        if not story.get("title"):
            continue
        items.append({
            "source": SOURCE,
            "name": story["title"],
            "url": story.get("url") or story.get("comments_url", ""),
            "metrics": {"score": story.get("score"),
                        "comments": story.get("comment_count"),
                        "tags": story.get("tags")},
            "detail": f"Discussion: {story.get('comments_url', '')}",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    try:
        payload = common.get_json("https://lobste.rs/hottest.json")
        return common.ok(SOURCE, LAYER, parse(payload))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
