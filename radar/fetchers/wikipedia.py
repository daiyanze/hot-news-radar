"""Wikipedia most-read fetcher: yesterday's top English articles (L2).

The Wikimedia pageviews API is free and keyless. This is the
radar's大众层 (mass layer) sensor and its main social-observation
feed: what the world actually looked up yesterday. It confirms
mass attention; it never originates a tech signal, so it sits in
L2 next to Google News. Meta pages (Main_Page, Special:…) are
filtered out.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import common

SOURCE = "wikipedia"
LAYER = 2

SKIP_PREFIXES = ("Special:", "Wikipedia:", "Help:", "File:", "Template:",
                 "Portal:", "Main_Page", "Category:", "Talk:")


def parse(payload: dict, limit: int = 25) -> list[dict]:
    """Pure parser for the pageviews top response (unit-tested)."""
    items = []
    blocks = payload.get("items") or []
    if not blocks:
        return items
    for article in blocks[0].get("articles", []):
        name_raw = article.get("article") or ""
        if not name_raw or name_raw.startswith(SKIP_PREFIXES):
            continue
        name = name_raw.replace("_", " ")
        items.append({
            "source": SOURCE,
            "name": name,
            "url": f"https://en.wikipedia.org/wiki/{name_raw}",
            "metrics": {"views": article.get("views"), "rank": article.get("rank")},
            "detail": "yesterday's most-read (en.wikipedia)",
        })
        if len(items) >= limit:
            break
    return items


def fetch(config: dict, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    cfg = config.get("sources", {}).get("wikipedia", {})
    limit = cfg.get("limit", 25)
    # The top list for a day is published the next day; ask for yesterday.
    day = now - timedelta(days=1)
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
           f"en.wikipedia/all-access/{day:%Y/%m/%d}")
    try:
        return common.ok(SOURCE, LAYER, parse(common.get_json(url), limit))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
