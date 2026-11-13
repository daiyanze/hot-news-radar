"""Official blogs fetcher: lab/company RSS bundle (L1).

First-hand announcements — OpenAI, DeepMind, Google Research,
Hugging Face, Mistral, NVIDIA, AWS ML, GitHub Blog, BAIR — read from
their own feeds (the T1 tier in AIHOT's source grading). All feeds
together count as ONE source for resonance: an announcement and its
own syndication must not look like independent confirmation.

Feed list lives in config (`sources.official_blogs.feeds`), so
users retarget the bundle at their own industry without code.
"""

from __future__ import annotations

from . import common

SOURCE = "official_blogs"
LAYER = 1

DEFAULT_FEEDS = [
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "Google Research", "url": "https://research.google/blog/rss/"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Mistral AI", "url": "https://mistral.ai/news/rss"},
    {"name": "NVIDIA Blog", "url": "https://blogs.nvidia.com/feed/"},
    {"name": "AWS Machine Learning", "url": "https://aws.amazon.com/blogs/machine-learning/feed/"},
    {"name": "GitHub Blog · AI & ML", "url": "https://github.blog/ai-and-ml/feed/"},
    {"name": "BAIR", "url": "https://bair.berkeley.edu/blog/feed.xml"},
]


def fetch(config: dict, now=None) -> dict:
    cfg = config.get("sources", {}).get("official_blogs", {})
    feeds = cfg.get("feeds", DEFAULT_FEEDS)
    return common.fetch_feed_bundle(SOURCE, LAYER, feeds, cfg.get("per_feed", 5))
