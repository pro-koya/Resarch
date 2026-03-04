"""
RSS Feed Client
feedparser でフィードを直接取得する。サーバー不要。
"""

import time
from calendar import timegm
from dataclasses import dataclass
from time import mktime

import feedparser
import yaml


@dataclass
class Article:
    id: str
    title: str
    url: str
    content: str  # HTML本文
    feed_title: str
    category: str
    published: int  # Unix timestamp
    is_starred: bool  # サーバーレスのため常に False
    is_read: bool  # サーバーレスのため常に False


def _parse_timestamp(entry) -> int:
    """feedparser のエントリからUnixタイムスタンプを取得。"""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return int(timegm(t))
    return int(time.time())


def fetch_feed(
    feed_url: str,
    feed_name: str,
    category: str,
    since_timestamp: int,
    limit: int = 50,
) -> list[Article]:
    """単一フィードから記事を取得。"""
    try:
        d = feedparser.parse(feed_url)
    except Exception as e:
        print(f"  [WARN] Feed parse failed: {feed_url} ({e})")
        return []

    if d.bozo and not d.entries:
        print(f"  [WARN] Feed error: {feed_url} ({d.bozo_exception})")
        return []

    feed_title = d.feed.get("title", feed_name) if d.feed else feed_name
    articles = []

    for entry in d.entries:
        ts = _parse_timestamp(entry)
        if ts < since_timestamp:
            continue

        # 本文: content > summary > description
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary or ""
        elif hasattr(entry, "description"):
            content = entry.description or ""

        url = getattr(entry, "link", "") or ""
        title = getattr(entry, "title", "(No Title)") or "(No Title)"
        entry_id = getattr(entry, "id", url) or url

        articles.append(Article(
            id=entry_id,
            title=title,
            url=url,
            content=content,
            feed_title=feed_title,
            category=category,
            published=ts,
            is_starred=False,
            is_read=False,
        ))

    # 新しい順にソート
    articles.sort(key=lambda a: a.published, reverse=True)
    return articles[:limit]


def fetch_category_feeds(
    feeds_config_path: str,
    category: str,
    since_timestamp: int,
    limit: int = 50,
) -> list[Article]:
    """feeds.yml から指定カテゴリの全フィードを取得してマージ。"""
    with open(feeds_config_path) as f:
        config = yaml.safe_load(f)

    cat_config = config.get("categories", {}).get(category)
    if not cat_config:
        return []

    all_articles: list[Article] = []
    for feed in cat_config.get("feeds", []):
        feed_url = feed["url"]
        feed_name = feed.get("name", feed_url)
        print(f"    Fetching: {feed_name}")
        articles = fetch_feed(feed_url, feed_name, category, since_timestamp, limit)
        all_articles.extend(articles)
        # レート制限を避ける最低限のsleep
        time.sleep(0.3)

    # 新しい順にソートして上位を返す
    all_articles.sort(key=lambda a: a.published, reverse=True)
    return all_articles[:limit]
