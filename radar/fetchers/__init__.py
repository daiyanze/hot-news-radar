"""Fetcher registry. Order is the methodology's layer order."""

from __future__ import annotations

from . import (appstore, arxiv, bluesky, civitai, dailypapers, devto, github,
               googlenews, hackernews, hfspaces, huggingface, lobsters,
               mastodon, media, official, openrouter, producthunt, reddit,
               showhn, sitemaps, wikipedia, x)

# L1 source layer first, then L2 fermentation. X stays first: when a
# token is configured it is the earliest signal of all.
FETCHERS = [x, official, github, hackernews, showhn, huggingface, hfspaces,
            openrouter, civitai, arxiv, dailypapers, bluesky, producthunt,
            reddit, media, devto, lobsters, mastodon, wikipedia, sitemaps,
            appstore, googlenews]

__all__ = ["FETCHERS"]
