"""Reddit fetcher: public JSON per configured subreddit, with the
public RSS feed as fallback (RSS carries titles/links but no scores).

Reddit frequently refuses unauthenticated JSON; each subreddit is
tried independently and the source reports which ones failed in its
note. If all fail the source is "missing", never faked.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from . import common

ATOM = "{http://www.w3.org/2005/Atom}"

SOURCE = "reddit"
LAYER = 2


def parse(payload: dict, subreddit: str) -> list[dict]:
    items = []
    for child in payload.get("data", {}).get("children", []):
        post = child.get("data", {})
        if post.get("stickied"):
            continue
        items.append({
            "source": SOURCE,
            "name": post.get("title", ""),
            "url": f"https://www.reddit.com{post.get('permalink', '')}",
            "metrics": {"score": post.get("score"), "comments": post.get("num_comments"),
                        "subreddit": subreddit},
            "detail": "",
        })
    return items


def parse_rss(xml_text: str, subreddit: str) -> list[dict]:
    """Atom feed fallback: title + link, no score/comment counts."""
    items = []
    root = ET.fromstring(xml_text)
    for entry in root.iter(f"{ATOM}entry"):
        title = entry.findtext(f"{ATOM}title") or ""
        link_el = entry.find(f"{ATOM}link")
        items.append({
            "source": SOURCE,
            "name": title,
            "url": link_el.get("href") if link_el is not None else "",
            "metrics": {"score": None, "comments": None, "subreddit": subreddit,
                        "via": "rss"},
            "detail": "",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    subs = config.get("sources", {}).get("reddit", {}).get("subreddits", [])
    items, failed, rss_subs = [], [], []
    for sub in subs:
        try:
            payload = common.get_json(f"https://www.reddit.com/r/{sub}/hot.json?limit=15")
            items.extend(parse(payload, sub))
            continue
        except common.FetchError:
            pass
        try:
            items.extend(parse_rss(
                common.get_text(f"https://www.reddit.com/r/{sub}/hot/.rss?limit=15"), sub))
            rss_subs.append(sub)
        except (common.FetchError, ET.ParseError):
            failed.append(sub)
    if not items:
        return common.missing(SOURCE, LAYER, f"all subreddits failed: {', '.join(failed)}")
    notes = []
    if rss_subs:
        notes.append(f"via RSS (no scores): {', '.join(rss_subs)}")
    if failed:
        notes.append(f"failed subreddits: {', '.join(failed)}")
    return common.ok(SOURCE, LAYER, items, "; ".join(notes))
