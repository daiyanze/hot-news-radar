"""Config loading: YAML first, JSON still welcome.

Search order (first hit wins): the explicit path, then
config.yaml, config.yml, config.json, config.example.yaml,
config.example.yml, config.example.json.

YAML parsing prefers PyYAML when it is installed (full language);
otherwise radar/yamlmini.py handles the subset our configs use,
so the tool stays zero-dependency.
"""

from __future__ import annotations

import json
import os

CANDIDATES = ["config.yaml", "config.yml", "config.json",
              "config.example.yaml", "config.example.yml", "config.example.json"]


def parse_yaml(text: str):
    try:
        import yaml
    except ImportError:
        from . import yamlmini
        return yamlmini.loads(text)
    return yaml.safe_load(text)


def load_config(path: str | None = None) -> dict:
    for candidate in [path, *CANDIDATES]:
        if candidate and os.path.exists(candidate):
            with open(candidate, encoding="utf-8") as fh:
                text = fh.read()
            if candidate.endswith((".yaml", ".yml")):
                return parse_yaml(text) or {}
            return json.loads(text)
    return {}
