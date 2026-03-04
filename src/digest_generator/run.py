"""
Digest Generator - メインエントリポイント
python -m digest_generator.run で実行
"""

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .api_client import Article, fetch_category_feeds
from .config import DigestConfig, load_config
from .renderer import DigestArticle, render_digest
from .summarizer import summarize

JST = timezone(timedelta(hours=9))


def determine_relevance(category: str, relevance_tags: list[str]) -> str:
    """ルールベースで転用示唆を決定。"""
    if not relevance_tags:
        return ""
    return relevance_tags[0]


def run():
    print(f"[{datetime.now(JST).isoformat()}] Digest generation started.")

    config = load_config()

    now = datetime.now(JST)
    since = now - timedelta(hours=config.lookback_hours)
    since_ts = int(since.timestamp())

    all_digest_articles: dict[str, list[DigestArticle]] = {}
    total_count = 0

    for cat_name, cat_config in config.categories.items():
        if total_count >= config.max_total_items:
            break

        remaining_budget = config.max_total_items - total_count
        effective_max = min(cat_config.max_items, remaining_budget)

        print(f"[{cat_name}] Fetching feeds (max={effective_max})...")

        articles = fetch_category_feeds(
            feeds_config_path=config.feeds_config,
            category=cat_name,
            since_timestamp=since_ts,
            limit=effective_max,
        )

        digest_articles = []
        for art in articles[:effective_max]:
            print(f"  Summarizing: {art.title[:60]}...")
            summary = summarize(
                art.content,
                method=config.summarizer,
                num_sentences=config.summary_sentences,
            )
            relevance = determine_relevance(cat_name, cat_config.relevance_tags)

            digest_articles.append(DigestArticle(
                title=art.title,
                source=art.feed_title,
                url=art.url,
                summary=summary,
                category=cat_name,
                relevance_tag=relevance,
                is_starred=art.is_starred,
            ))

        if digest_articles:
            all_digest_articles[cat_name] = digest_articles
            total_count += len(digest_articles)
            print(f"  -> {len(digest_articles)} articles processed.")

    # Markdown 生成
    md_content = render_digest(all_digest_articles, now, config.lookback_hours)

    # 出力
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = now.strftime("%Y-%m-%d")
    dated_file = output_dir / f"{date_str}.md"
    latest_file = output_dir / "latest.md"

    dated_file.write_text(md_content, encoding="utf-8")
    shutil.copy2(dated_file, latest_file)

    # GitHub Pages 用 HTML も生成
    _generate_html(output_dir, md_content, date_str)

    print(f"[{datetime.now(JST).isoformat()}] Digest saved: {dated_file}")
    print(f"  Total articles: {total_count}")
    print("Done.")


def _generate_html(output_dir: Path, md_content: str, date_str: str):
    """Markdown → HTML 変換して GitHub Pages 用に出力。"""
    import markdown
    from jinja2 import Template

    html_body = markdown.markdown(md_content, extensions=["extra", "sane_lists"])

    template_path = Path("docs/template.html")
    if template_path.exists():
        template = Template(template_path.read_text(encoding="utf-8"))
    else:
        template = Template(DEFAULT_TEMPLATE)

    html = template.render(
        title=f"Daily Digest - {date_str}",
        content=html_body,
        date=date_str,
    )

    (output_dir / f"{date_str}.html").write_text(html, encoding="utf-8")
    (output_dir / "index.html").write_text(html, encoding="utf-8")


DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root { --bg: #0d1117; --fg: #e6edf3; --muted: #8b949e; --accent: #58a6ff; --border: #30363d; --card: #161b22; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
           background: var(--bg); color: var(--fg); line-height: 1.7; padding: 2rem; max-width: 800px; margin: 0 auto; }
    h1 { font-size: 1.8rem; margin-bottom: 0.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
    h2 { font-size: 1.3rem; color: var(--accent); margin-top: 2rem; margin-bottom: 0.8rem; }
    h3 { font-size: 1.05rem; margin-top: 1.2rem; }
    p { margin: 0.5rem 0; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    hr { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }
    blockquote { border-left: 3px solid var(--accent); padding: 0.5rem 1rem; margin: 0.8rem 0;
                 background: var(--card); border-radius: 0 6px 6px 0; color: var(--muted); }
    strong { color: var(--fg); }
    code { background: var(--card); padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.9em; }
    .footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.85rem; }
  </style>
</head>
<body>
  {{ content }}
  <div class="footer">
    <p>Powered by <a href="#">digest-generator</a> &middot; GitHub Actions + Pages</p>
  </div>
</body>
</html>"""


if __name__ == "__main__":
    run()
