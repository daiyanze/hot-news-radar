"""Mastodon trends fetcher: trending links and tags (L2).

The public trends API of a large instance (default mastodon.social)
needs no key and gives a social-chatter signal while X has no free
read API: `history` on each trend counts distinct accounts posting
about it per day — a built-in resonance measure.
"""

from __future__ import annotations

from . import common

SOURCE = "mastodon"
LAYER = 2


def _accounts(history: list) -> int | None:
    if not history:
        return None
    try:
        return int(history[0].get("accounts", 0))
    except (TypeError, ValueError):
        return None


def parse_links(payload: list) -> list[dict]:
    """Pure parser for trending links (unit-tested)."""
    items = []
    for link in payload:
        if not link.get("title"):
            continue
        items.append({
            "source": SOURCE,
            "name": link["title"],
            "url": link.get("url", ""),
            "metrics": {"accounts_today": _accounts(link.get("history") or []),
                        "provider": link.get("provider_name")},
            "detail": (link.get("description") or "")[:240],
        })
    return items


def parse_tags(payload: list) -> list[dict]:
    """Pure parser for trending tags (unit-tested)."""
    items = []
    for tag in payload:
        if not tag.get("name"):
            continue
        items.append({
            "source": SOURCE,
            "name": f"#{tag['name']}",
            "url": tag.get("url", ""),
            "metrics": {"accounts_today": _accounts(tag.get("history") or [])},
            "detail": "trending hashtag",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    cfg = config.get("sources", {}).get("mastodon", {})
    instance = cfg.get("instance", "mastodon.social")
    limit = cfg.get("limit", 20)
    items, failed = [], 0
    for kind, parser in (("links", parse_links), ("tags", parse_tags)):
        try:
            payload = common.get_json(
                f"https://{instance}/api/v1/trends/{kind}?limit={limit}")
            items.extend(parser(payload))
        except common.FetchError:
            failed += 1
    if failed == 2:
        return common.missing(SOURCE, LAYER, f"trends API failed on {instance}")
    return common.ok(SOURCE, LAYER, items, "one trends endpoint failed" if failed else "")
