"""DEV (dev.to) fetcher: top developer articles (L2).

DEV's public API is free and keyless. It is a practitioner
fermentation signal: what working developers are reading and
reacting to, complementary to HN's front page.
"""

from __future__ import annotations

from . import common

SOURCE = "devto"
LAYER = 2


def parse(payload: list) -> list[dict]:
    """Pure parser for the DEV articles response (unit-tested)."""
    items = []
    for article in payload:
        if not article.get("title"):
            continue
        items.append({
            "source": SOURCE,
            "name": article["title"],
            "url": article.get("url", ""),
            "metrics": {"reactions": article.get("public_reactions_count"),
                        "comments": article.get("comments_count"),
                        "reading_time": article.get("reading_time_minutes")},
            "detail": article.get("description") or "",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    cfg = config.get("sources", {}).get("devto", {})
    days = cfg.get("top_days", 1)
    per_page = cfg.get("per_page", 30)
    try:
        payload = common.get_json(
            f"https://dev.to/api/articles?top={days}&per_page={per_page}")
        return common.ok(SOURCE, LAYER, parse(payload))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
