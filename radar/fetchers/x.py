"""X fetcher. There is no free official read API for trends, so by
default this source reports itself missing and the agent covers X
by web scan (the current production behaviour). Set X_BEARER_TOKEN
plus `accounts` in config to enable recent-search per account.
"""

from __future__ import annotations

import os
from urllib.parse import quote

from . import common

SOURCE = "x"
LAYER = 1


def parse(payload: dict) -> list[dict]:
    items = []
    for tweet in payload.get("data", []):
        metrics = tweet.get("public_metrics", {})
        items.append({
            "source": SOURCE,
            "name": (tweet.get("text") or "")[:120],
            "url": f"https://x.com/i/web/status/{tweet.get('id')}",
            "metrics": {"likes": metrics.get("like_count")},
            "detail": "",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    token = os.environ.get("X_BEARER_TOKEN")
    accounts = config.get("sources", {}).get("x", {}).get("accounts", [])
    if not token:
        return common.missing(SOURCE, LAYER,
                              "X_BEARER_TOKEN not set; covered by agent web scan")
    if not accounts:
        return common.missing(SOURCE, LAYER, "no accounts configured in config x.accounts")
    items = []
    for account in accounts:
        query = quote(f"from:{account}")
        url = (f"https://api.x.com/2/tweets/search/recent?query={query}"
               "&tweet.fields=public_metrics&max_results=10")
        try:
            items.extend(parse(common.get_json(
                url, headers={"Authorization": f"Bearer {token}"})))
        except common.FetchError:
            continue
    if not items:
        return common.missing(SOURCE, LAYER, "X API returned nothing for configured accounts")
    return common.ok(SOURCE, LAYER, items)
