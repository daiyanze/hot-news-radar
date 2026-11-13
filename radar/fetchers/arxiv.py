"""arXiv fetcher: newest papers in the configured categories (L1).

The arXiv API is free and keyless. Papers are the earliest public
trace of research directions — they arrive days before the blog
posts and threads that make a topic trend. We take the newest
submissions per scan; the agent judges which ones name something new.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

from . import common

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"

SOURCE = "arxiv"
LAYER = 1


def parse(xml_text: str) -> list[dict]:
    """Pure parser for the arXiv Atom response (unit-tested)."""
    items = []
    root = ET.fromstring(xml_text)
    for entry in root.iter(f"{ATOM}entry"):
        title = re.sub(r"\s+", " ", entry.findtext(f"{ATOM}title") or "").strip()
        link = entry.findtext(f"{ATOM}id") or ""
        if not title or not link:
            continue
        primary = entry.find(f"{ARXIV}primary_category")
        summary = re.sub(r"\s+", " ", entry.findtext(f"{ATOM}summary") or "").strip()
        items.append({
            "source": SOURCE,
            "name": title,
            "url": link,
            "metrics": {"published": entry.findtext(f"{ATOM}published"),
                        "category": primary.get("term") if primary is not None else None,
                        "authors": len(entry.findall(f"{ATOM}author"))},
            "detail": summary[:240],
        })
    return items


def fetch(config: dict, now=None) -> dict:
    cfg = config.get("sources", {}).get("arxiv", {})
    cats = cfg.get("categories", ["cs.AI", "cs.CL", "cs.LG"])
    max_results = cfg.get("max_results", 30)
    query = quote(" OR ".join(f"cat:{c}" for c in cats))
    url = (f"https://export.arxiv.org/api/query?search_query={query}"
           f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}")
    try:
        return common.ok(SOURCE, LAYER, parse(common.get_text(url)))
    except (common.FetchError, ET.ParseError) as exc:
        return common.missing(SOURCE, LAYER, str(exc))
