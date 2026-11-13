"""HF Daily Papers fetcher: community-curated papers (L1).

Where arXiv is the firehose, Daily Papers is the same research
stream after the Hugging Face community has upvoted and discussed
it for a day — the pre-filtered version. The pair complement each
other: arXiv for earliest, Daily Papers for peer-confirmed.
"""

from __future__ import annotations

import re

from . import common

SOURCE = "daily_papers"
LAYER = 1


def parse(payload: list) -> list[dict]:
    """Pure parser for the daily_papers response (unit-tested)."""
    items = []
    for entry in payload:
        paper = entry.get("paper") or {}
        title = re.sub(r"\s+", " ", paper.get("title") or entry.get("title") or "").strip()
        paper_id = paper.get("id")
        if not title or not paper_id:
            continue
        items.append({
            "source": SOURCE,
            "name": title,
            "url": f"https://huggingface.co/papers/{paper_id}",
            "metrics": {"upvotes": paper.get("upvotes"),
                        "comments": entry.get("numComments"),
                        "authors": len(paper.get("authors") or []),
                        "github_repo": paper.get("githubRepo")},
            "detail": re.sub(r"\s+", " ", paper.get("summary") or "")[:240],
        })
    return items


def fetch(config: dict, now=None) -> dict:
    limit = config.get("sources", {}).get("daily_papers", {}).get("limit", 30)
    try:
        payload = common.get_json(f"https://huggingface.co/api/daily_papers?limit={limit}")
        return common.ok(SOURCE, LAYER, parse(payload))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
