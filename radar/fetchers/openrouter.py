"""OpenRouter fetcher: the newest models on the routing platform (L1).

OpenRouter's model list is a free keyless JSON API. A model appearing
here is a launch signal: providers list models the day they ship,
often before the announcement thread peaks. Sorted newest-first;
models created within `new_days` are flagged.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import common

SOURCE = "openrouter"
LAYER = 1
NEW_DAYS = 14


def parse(payload: dict, now: datetime, new_days: int = NEW_DAYS,
          limit: int = 30) -> list[dict]:
    """Pure parser for the OpenRouter models response (unit-tested)."""
    models = []
    for model in payload.get("data", []):
        created = model.get("created")
        if not model.get("id") or not created:
            continue
        created_dt = datetime.fromtimestamp(created, tz=timezone.utc)
        models.append((created_dt, model))
    models.sort(key=lambda pair: pair[0], reverse=True)
    items = []
    for created_dt, model in models[:limit]:
        pricing = model.get("pricing") or {}
        items.append({
            "source": SOURCE,
            "name": model.get("name") or model["id"],
            "url": f"https://openrouter.ai/{model['id']}",
            "metrics": {"model_id": model["id"],
                        "created": created_dt.date().isoformat(),
                        "is_new": (now - created_dt).days <= new_days,
                        "context_length": model.get("context_length"),
                        "prompt_price": pricing.get("prompt")},
            "detail": (model.get("description") or "")[:240],
        })
    return items


def fetch(config: dict, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    cfg = config.get("sources", {}).get("openrouter", {})
    try:
        payload = common.get_json("https://openrouter.ai/api/v1/models")
        return common.ok(SOURCE, LAYER,
                         parse(payload, now, cfg.get("new_days", NEW_DAYS),
                               cfg.get("limit", 30)))
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
