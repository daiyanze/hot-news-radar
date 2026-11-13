"""Hugging Face Spaces fetcher: trending demos, flagging new faces (L1).

Spaces are the demos people actually try — new-term-radar reads
models AND Spaces for exactly this reason. Same trending API shape
as the models fetcher, different endpoint and URL space, and tracked
as its own source so the 14-day review can score it separately.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import common

SOURCE = "hf_spaces"
LAYER = 1
NEW_FACE_DAYS = 30


def parse(payload: list, now: datetime) -> list[dict]:
    """Pure parser for the HF spaces response (unit-tested)."""
    items = []
    for space in payload:
        created_raw = space.get("createdAt")
        new_face = False
        if created_raw:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            new_face = (now - created).days <= NEW_FACE_DAYS
        items.append({
            "source": SOURCE,
            "name": space["id"],
            "url": f"https://huggingface.co/spaces/{space['id']}",
            "metrics": {"likes": space.get("likes"),
                        "trending_score": space.get("trendingScore"),
                        "sdk": space.get("sdk"),
                        "new_face": new_face},
            "detail": "",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    top_n = config.get("sources", {}).get("hf_spaces", {}).get("top_n", 50)
    try:
        payload = common.get_json(
            f"https://huggingface.co/api/spaces?sort=trendingScore&direction=-1&limit={top_n}")
        return common.ok(SOURCE, LAYER, parse(payload, now))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
