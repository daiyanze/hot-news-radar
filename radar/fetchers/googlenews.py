"""Google News fetcher via its public RSS search feeds (L2 only:
confirms stories already spreading; never a discovery source)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote

from . import common

SOURCE = "google_news"
LAYER = 2


def parse(xml_text: str) -> list[dict]:
    items = []
    root = ET.fromstring(xml_text)
    for node in root.iter("item"):
        title = node.findtext("title") or ""
        link = node.findtext("link") or ""
        source_el = node.find("source")
        items.append({
            "source": SOURCE,
            "name": title,
            "url": link,
            "metrics": {"outlet": source_el.text if source_el is not None else None,
                        "published": node.findtext("pubDate")},
            "detail": "",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    topics = config.get("sources", {}).get("google_news", {}).get("topics", ["ai"])
    items, failed = [], 0
    for topic in topics:
        url = (f"https://news.google.com/rss/search?q={quote(topic)}"
               "&hl=en-US&gl=US&ceid=US:en")
        try:
            items.extend(parse(common.get_text(url))[:20])
        except (common.FetchError, ET.ParseError):
            failed += 1
    if failed == len(topics):
        return common.missing(SOURCE, LAYER, "all Google News feeds failed")
    return common.ok(SOURCE, LAYER, items, f"{failed} feed(s) failed" if failed else "")
