"""Civitai fetcher: newest community models (L1).

The image/video generation community ships fine-tunes and LoRAs
daily; a base model that suddenly spawns Civitai activity is an
early signal (new-term-radar lists Civitai among its free
just-listed sources). Public API, no key; SFW only.
"""

from __future__ import annotations

from . import common

SOURCE = "civitai"
LAYER = 1


def parse(payload: dict) -> list[dict]:
    """Pure parser for the Civitai models response (unit-tested)."""
    items = []
    for model in payload.get("items", []):
        stats = model.get("stats") or {}
        if not model.get("name"):
            continue
        items.append({
            "source": SOURCE,
            "name": model["name"],
            "url": f"https://civitai.com/models/{model.get('id')}",
            "metrics": {"downloads": stats.get("downloadCount"),
                        "thumbs_up": stats.get("thumbsUpCount"),
                        "type": model.get("type"),
                        "base_models": [v.get("baseModel") for v in
                                        (model.get("modelVersions") or [])[:1]]},
            "detail": "",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    cfg = config.get("sources", {}).get("civitai", {})
    limit = cfg.get("limit", 20)
    try:
        payload = common.get_json(
            f"https://civitai.com/api/v1/models?limit={limit}&sort=Newest&nsfw=false")
        return common.ok(SOURCE, LAYER, parse(payload))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
