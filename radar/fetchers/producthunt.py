"""Product Hunt fetcher. Two routes, both honest:

- With PRODUCTHUNT_TOKEN set: the GraphQL API (votes/comments).
- Without a token: the public Atom feed at producthunt.com/feed
  (titles/links only, no vote counts — noted in the result).

The feed route means this source no longer needs the agent's web
scan as a fallback.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from . import common

SOURCE = "producthunt"
LAYER = 1

QUERY = """
{ posts(first: 20, order: RANKING) {
    edges { node { name tagline url votesCount commentsCount } } } }
"""


def parse(payload: dict) -> list[dict]:
    items = []
    edges = payload.get("data", {}).get("posts", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        items.append({
            "source": SOURCE,
            "name": node.get("name", ""),
            "url": node.get("url", ""),
            "metrics": {"votes": node.get("votesCount"), "comments": node.get("commentsCount")},
            "detail": node.get("tagline") or "",
        })
    return items


def parse_feed(xml_text: str) -> list[dict]:
    """Pure parser for the public Atom feed (unit-tested)."""
    return common.parse_feed(xml_text, SOURCE, "Product Hunt", limit=30)


def _fetch_feed() -> dict:
    try:
        items = parse_feed(common.get_text("https://www.producthunt.com/feed"))
        if not items:
            return common.missing(SOURCE, LAYER, "Product Hunt feed returned no items")
        return common.ok(SOURCE, LAYER, items, "via public Atom feed (no vote counts)")
    except (common.FetchError, ET.ParseError) as exc:
        return common.missing(SOURCE, LAYER, f"Product Hunt feed failed: {exc}")


def fetch(config: dict, now=None) -> dict:
    token = os.environ.get("PRODUCTHUNT_TOKEN")
    if not token:
        return _fetch_feed()
    try:
        import json as _json
        import urllib.request
        req = urllib.request.Request(
            "https://api.producthunt.com/v2/api/graphql",
            data=_json.dumps({"query": QUERY}).encode(),
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json",
                     "User-Agent": common.USER_AGENT})
        with urllib.request.urlopen(req, timeout=common.TIMEOUT) as resp:
            payload = _json.loads(resp.read().decode("utf-8"))
        return common.ok(SOURCE, LAYER, parse(payload))
    except Exception as exc:
        return common.missing(SOURCE, LAYER, f"Product Hunt API failed: {exc}")
