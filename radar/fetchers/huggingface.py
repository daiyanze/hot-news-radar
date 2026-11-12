"""Hugging Face fetcher: trending models, flagging new faces."""

from __future__ import annotations

from datetime import datetime, timezone

from . import common

SOURCE = "huggingface"
LAYER = 1
NEW_FACE_DAYS = 30


def parse(payload: list, now: datetime) -> list[dict]:
    items = []
    for model in payload:
        created_raw = model.get("createdAt")
        new_face = False
        if created_raw:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            new_face = (now - created).days <= NEW_FACE_DAYS
        items.append({
            "source": SOURCE,
            "name": model["id"],
            "url": f"https://huggingface.co/{model['id']}",
            "metrics": {"likes": model.get("likes"), "downloads": model.get("downloads"),
                        "new_face": new_face},
            "detail": "",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    top_n = config.get("sources", {}).get("huggingface", {}).get("top_n", 50)
    try:
        payload = common.get_json(
            f"https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit={top_n}")
        return common.ok(SOURCE, LAYER, parse(payload, now))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
