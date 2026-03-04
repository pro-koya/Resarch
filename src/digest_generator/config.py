"""Digest configuration loader."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class CategoryConfig:
    name: str
    max_items: int = 3
    priority: str = "unread_top"  # starred_first / unread_top
    relevance_tags: list[str] = field(default_factory=list)


@dataclass
class DigestConfig:
    max_total_items: int = 15
    lookback_hours: int = 24
    summarizer: str = "extractive"
    summary_sentences: int = 3
    output_dir: str = "docs/digests"
    feeds_config: str = "config/feeds.yml"
    categories: dict[str, CategoryConfig] = field(default_factory=dict)


def load_config(path: str = "config/digest.yml") -> DigestConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    g = raw.get("global", {})

    # 環境変数で上書き
    summarizer = os.environ.get("SUMMARIZER", g.get("summarizer", "extractive"))

    config = DigestConfig(
        max_total_items=g.get("max_total_items", 15),
        lookback_hours=g.get("lookback_hours", 24),
        summarizer=summarizer,
        summary_sentences=g.get("summary_sentences", 3),
        output_dir=g.get("output_dir", "docs/digests"),
        feeds_config=g.get("feeds_config", "config/feeds.yml"),
    )

    for cat_name, cat_raw in raw.get("categories", {}).items():
        config.categories[cat_name] = CategoryConfig(
            name=cat_name,
            max_items=cat_raw.get("max_items", 3),
            priority=cat_raw.get("priority", "unread_top"),
            relevance_tags=cat_raw.get("relevance_tags", []),
        )

    return config
