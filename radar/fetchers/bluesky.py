"""Bluesky fetcher: configured accounts' public RSS feeds (L1).

Bluesky's search API needs auth, but every profile publishes a
plain RSS feed of its posts — the keyless way to follow the same
labs and bloggers the X config names. Each account is one feed;
all accounts together count as ONE source (like the X fetcher).

Bluesky RSS items carry no <title>: the post text lives in
<description>, so the first line becomes the candidate name.
Defaults were verified live on 2026-11-13 (handles whose feeds
were empty or missing are not in the list).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from . import common

SOURCE = "bluesky"
LAYER = 1

DEFAULT_ACCOUNTS = [
    "simonwillison.net",      # Simon Willison
    "karpathy.bsky.social",   # Andrej Karpathy
    "gdb.bsky.social",        # Greg Brockman
    "techcrunch.com",         # TechCrunch
    "theverge.com",           # The Verge
    "wired.com",              # WIRED
    "arstechnica.com",        # Ars Technica
]


def parse(xml_text: str, handle: str, limit: int = 10) -> list[dict]:
    """Pure parser for one profile's RSS feed (unit-tested)."""
    items = []
    root = ET.fromstring(xml_text)
    for node in root.findall("./channel/item"):
        link = (node.findtext("link") or "").strip()
        text = re.sub(r"\s+", " ", node.findtext("description") or "").strip()
        if not link or not text:
            continue
        items.append({
            "source": SOURCE,
            "name": text[:140],
            "url": link,
            "metrics": {"account": handle, "published": node.findtext("pubDate")},
            "detail": text[:240],
        })
        if len(items) >= limit:
            break
    return items


def fetch(config: dict, now=None) -> dict:
    cfg = config.get("sources", {}).get("bluesky", {})
    accounts = cfg.get("accounts", DEFAULT_ACCOUNTS)
    per_account = cfg.get("per_account", 10)
    items, failed = [], []
    for handle in accounts:
        try:
            items.extend(parse(
                common.get_text(f"https://bsky.app/profile/{handle}/rss"),
                handle, per_account))
        except (common.FetchError, ET.ParseError):
            failed.append(handle)
    if not items:
        return common.missing(SOURCE, LAYER, f"all Bluesky feeds failed: {', '.join(failed)}")
    note = f"failed accounts: {', '.join(failed)}" if failed else ""
    return common.ok(SOURCE, LAYER, items, note)
