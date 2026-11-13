"""Shared HTTP helpers for fetchers.

Every fetcher returns a result dict:
  {"source": str, "layer": int, "status": "ok" | "missing",
   "items": [candidate, ...], "note": str}

A candidate is a normalized dict:
  {"source": str, "name": str, "url": str, "metrics": {...}, "detail": str}

Fetchers never raise: a failure becomes status "missing" with the
reason in "note". The radar methodology requires reporting a source
as missing rather than faking its content.
"""

from __future__ import annotations

import gzip
import json
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = "triple-sigma/0.5.1 (+https://github.com/daiyanze/triple-sigma)"
TIMEOUT = 25

ATOM = "{http://www.w3.org/2005/Atom}"


class FetchError(Exception):
    pass


def _read_body(resp) -> bytes:
    raw = resp.read()
    # Some servers (e.g. DeepMind's blog) answer gzip regardless of
    # the request's Accept-Encoding; decode transparently.
    if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(raw)
        except OSError:
            return raw
    return raw


def get_json(url: str, headers: dict | None = None) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(_read_body(resp).decode("utf-8"))
    except Exception as exc:  # network, HTTP, decode — all mean "missing"
        raise FetchError(f"{url}: {exc}") from exc


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return _read_body(resp).decode("utf-8", errors="replace")
    except Exception as exc:
        raise FetchError(f"{url}: {exc}") from exc


def parse_feed(xml_text: str, source: str, outlet: str, limit: int = 5) -> list[dict]:
    """Parse an RSS 2.0 or Atom feed into normalized candidates.

    Shared by the RSS-bundle fetchers (official blogs, tech media).
    Pure function — unit-tested. Raises ET.ParseError on bad XML.
    """
    items = []
    root = ET.fromstring(xml_text)
    # RSS 2.0: channel/item
    nodes = root.findall("./channel/item")
    if nodes:
        for node in nodes[:limit]:
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            if not title or not link:
                continue
            items.append({
                "source": source, "name": title, "url": link,
                "metrics": {"outlet": outlet, "published": node.findtext("pubDate")},
                "detail": "",
            })
        return items
    # Atom: feed/entry (link is an attribute, rel=alternate preferred)
    for node in root.iter(f"{ATOM}entry"):
        title = (node.findtext(f"{ATOM}title") or "").strip()
        link = ""
        for link_el in node.findall(f"{ATOM}link"):
            if link_el.get("rel") in (None, "alternate"):
                link = link_el.get("href") or ""
                break
        if not title or not link:
            continue
        published = node.findtext(f"{ATOM}published") or node.findtext(f"{ATOM}updated")
        items.append({
            "source": source, "name": title, "url": link,
            "metrics": {"outlet": outlet, "published": published},
            "detail": "",
        })
        if len(items) >= limit:
            break
    return items


def fetch_feed_bundle(source: str, layer: int, feeds: list[dict],
                      per_feed: int = 5) -> dict:
    """Fetch a configured list of RSS/Atom feeds as ONE source.

    A bundle counts as a single source for cross-source resonance:
    ten outlets echoing one story must not fake ten sources. Per-feed
    failures are reported in the note, never hidden.
    """
    items, failed = [], []
    for feed in feeds:
        try:
            items.extend(parse_feed(get_text(feed["url"]), source,
                                    feed.get("name", feed["url"]), per_feed))
        except (FetchError, ET.ParseError):
            failed.append(feed.get("name", feed["url"]))
    if not items:
        return missing(source, layer, f"all feeds failed: {', '.join(failed)}")
    note = f"failed feeds: {', '.join(failed)}" if failed else ""
    return ok(source, layer, items, note)


def missing(source: str, layer: int, note: str) -> dict:
    return {"source": source, "layer": layer, "status": "missing", "items": [], "note": note}


def ok(source: str, layer: int, items: list[dict], note: str = "") -> dict:
    return {"source": source, "layer": layer, "status": "ok", "items": items, "note": note}
