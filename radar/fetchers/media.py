"""Tech media fetcher: media + independent-voice RSS bundle (L2).

The fermentation layer's press side (AIHOT's T2 tier): TechCrunch,
The Verge, Ars Technica, MIT Technology Review, The Decoder, plus
independent voices whose posts routinely move topics (Simon
Willison, Import AI, Latent Space). One story echoed by six outlets
is still one source — the bundle counts once for resonance.
"""

from __future__ import annotations

from . import common

SOURCE = "tech_media"
LAYER = 2

DEFAULT_FEEDS = [
    {"name": "TechCrunch · AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "The Verge · AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"name": "Ars Technica · AI", "url": "https://arstechnica.com/ai/feed/"},
    {"name": "MIT Technology Review · AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed"},
    {"name": "The Decoder", "url": "https://the-decoder.com/feed/"},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/"},
    {"name": "Import AI", "url": "https://importai.substack.com/feed"},
    {"name": "Latent Space", "url": "https://www.latent.space/feed"},
]


def fetch(config: dict, now=None) -> dict:
    cfg = config.get("sources", {}).get("tech_media", {})
    feeds = cfg.get("feeds", DEFAULT_FEEDS)
    return common.fetch_feed_bundle(SOURCE, LAYER, feeds, cfg.get("per_feed", 5))
