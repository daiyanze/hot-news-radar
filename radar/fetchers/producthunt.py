"""Product Hunt fetcher. The GraphQL API needs a developer token:
set PRODUCTHUNT_TOKEN to enable. Without it the source reports
itself missing with the reason — the agent's web scan covers
Product Hunt in the meantime (see SKILL.md).
"""

from __future__ import annotations

import os
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


def fetch(config: dict, now=None) -> dict:
    token = os.environ.get("PRODUCTHUNT_TOKEN")
    if not token:
        return common.missing(SOURCE, LAYER,
                              "PRODUCTHUNT_TOKEN not set; covered by agent web scan")
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
