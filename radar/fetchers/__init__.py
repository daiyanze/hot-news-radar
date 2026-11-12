"""Fetcher registry. Order is the methodology's layer order."""

from __future__ import annotations

from . import github, googlenews, hackernews, huggingface, producthunt, reddit, x

FETCHERS = [x, github, hackernews, huggingface, producthunt, reddit, googlenews]

__all__ = ["FETCHERS"]
