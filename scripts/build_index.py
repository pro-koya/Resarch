#!/usr/bin/env python3
"""
docs/digests/ 内のダイジェスト一覧から docs/index.html を生成する。
GitHub Pages のトップページ。
"""

from pathlib import Path

DOCS_DIR = Path("docs")
DIGESTS_DIR = DOCS_DIR / "digests"


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 日付付きHTMLファイルを収集（index.html除く）
    digest_files = sorted(
        [f for f in DIGESTS_DIR.glob("*.html") if f.name != "index.html"],
        reverse=True,
    )

    entries = ""
    for f in digest_files:
        date = f.stem
        entries += f'      <li><a href="digests/{f.name}">{date}</a></li>\n'

    if not entries:
        entries = "      <li>まだダイジェストがありません。GitHub Actions を手動実行してください。</li>\n"

    latest_link = ""
    if digest_files:
        latest = digest_files[0].name
        latest_link = f'<p><a href="digests/index.html" class="latest-btn">Latest Digest を読む</a></p>'

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daily Digest Archive</title>
  <style>
    :root {{ --bg: #0d1117; --fg: #e6edf3; --muted: #8b949e; --accent: #58a6ff; --border: #30363d; --card: #161b22; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
           background: var(--bg); color: var(--fg); line-height: 1.7; padding: 2rem; max-width: 800px; margin: 0 auto; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 1rem; }}
    ul {{ list-style: none; margin-top: 1rem; }}
    li {{ padding: 0.5rem 0; border-bottom: 1px solid var(--border); }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .latest-btn {{ display: inline-block; margin: 1rem 0; padding: 0.6rem 1.5rem; background: var(--accent);
                   color: var(--bg); border-radius: 6px; font-weight: bold; }}
    .latest-btn:hover {{ opacity: 0.9; text-decoration: none; }}
    .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>Daily Digest Archive</h1>
  {latest_link}
  <h2>Archive</h2>
  <ul>
{entries}  </ul>
  <div class="footer">
    <p>Powered by GitHub Actions + Pages</p>
  </div>
</body>
</html>"""

    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"Built index.html with {len(digest_files)} entries.")


if __name__ == "__main__":
    main()
