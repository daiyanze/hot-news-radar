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

import json
import urllib.request

USER_AGENT = "hot-news-radar/0.2 (+https://github.com/daiyanze/hot-news-radar)"
TIMEOUT = 25


class FetchError(Exception):
    pass


def get_json(url: str, headers: dict | None = None) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network, HTTP, decode — all mean "missing"
        raise FetchError(f"{url}: {exc}") from exc


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise FetchError(f"{url}: {exc}") from exc


def missing(source: str, layer: int, note: str) -> dict:
    return {"source": source, "layer": layer, "status": "missing", "items": [], "note": note}


def ok(source: str, layer: int, items: list[dict], note: str = "") -> dict:
    return {"source": source, "layer": layer, "status": "ok", "items": items, "note": note}
