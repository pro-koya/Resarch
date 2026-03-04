# Daily Digest — GitHub Actions + Pages セットアップガイド

## 設計方針

**サーバー不要・完全無料**のアーキテクチャ:

1. **GitHub Actions** — cron スケジュールで毎朝 06:30 JST にダイジェスト生成を実行
2. **feedparser** — RSS/Atom フィードを直接取得。FreshRSS等のサーバー不要
3. **Python 抽出型要約** — 外部API不要。頻度ベースで重要文を抽出（LLM拡張も可能）
4. **GitHub Pages** — 生成した HTML を自動デプロイ。カスタムドメイン不要
5. **Git = バックアップ** — ダイジェストは全てリポジトリにコミットされるため自動的に履歴管理

---

## ディレクトリ構成

```
.
├── .github/workflows/
│   └── digest.yml              # GitHub Actions ワークフロー
├── config/
│   ├── feeds.yml               # フィードソース定義
│   └── digest.yml              # ダイジェスト生成ルール
├── src/
│   └── digest_generator/
│       ├── __init__.py
│       ├── __main__.py
│       ├── run.py              # エントリポイント
│       ├── api_client.py       # RSS直接取得クライアント
│       ├── summarizer.py       # 要約エンジン
│       ├── config.py           # 設定ローダー
│       └── renderer.py         # Markdown レンダラー
├── scripts/
│   └── build_index.py          # アーカイブページ生成
├── docs/                       # GitHub Pages 配信ディレクトリ
│   ├── index.html              # トップ（アーカイブ一覧）
│   └── digests/
│       ├── index.html          # 最新ダイジェスト
│       ├── YYYY-MM-DD.html     # 日付別ダイジェスト
│       ├── latest.md           # 最新MD
│       └── YYYY-MM-DD.md       # 日付別MD
├── requirements.txt
├── PLAN.md
└── SETUP.md
```

---

## セットアップ手順

### 1. GitHubリポジトリを作成

```bash
cd /path/to/this/project

git init
git add .
git commit -m "initial commit"

# GitHub でリポジトリを作成後:
git remote add origin git@github.com:<YOUR_USER>/<REPO_NAME>.git
git branch -M main
git push -u origin main
```

### 2. GitHub Pages を有効化

1. リポジトリの **Settings** > **Pages**
2. **Source** → 「GitHub Actions」を選択

### 3. （オプション）LLM要約を有効化する場合

リポジトリの **Settings** > **Secrets and variables** > **Actions** で以下を設定:

| Secret Name   | 値                                         |
|---------------|--------------------------------------------|
| `SUMMARIZER`  | `llm`                                      |
| `LLM_API_KEY` | APIキー                                    |
| `LLM_API_URL` | エンドポイントURL                           |
| `LLM_MODEL`   | モデル名                                   |

未設定の場合は自動的に extractive（抽出型要約）が使われます。

### 4. 初回テスト実行

1. リポジトリの **Actions** タブを開く
2. 左側の「Daily Digest」ワークフローを選択
3. **Run workflow** ボタンをクリック（手動実行）
4. 完了後、**Pages URL**（`https://<user>.github.io/<repo>/`）にアクセス

---

## 最小実行コマンド集（コピペ用）

```bash
# ---------- 初回セットアップ ----------
git init && git add . && git commit -m "initial commit"
# → GitHub でリポジトリ作成
git remote add origin git@github.com:<USER>/<REPO>.git
git push -u origin main
# → Settings > Pages > Source: GitHub Actions

# ---------- ローカルで手動テスト ----------
pip install -r requirements.txt
PYTHONPATH=src python -m digest_generator.run
# → docs/digests/ にファイルが生成される
python scripts/build_index.py
# → docs/index.html が生成される
open docs/digests/index.html                     # ブラウザで確認

# ---------- フィード管理 ----------
nano config/feeds.yml                            # フィード編集
git add config/feeds.yml && git commit -m "update feeds" && git push

# ---------- ダイジェストルール変更 ----------
nano config/digest.yml                           # ルール編集
git add config/digest.yml && git commit -m "update digest rules" && git push

# ---------- 手動でワークフロー実行 ----------
gh workflow run digest.yml                       # GitHub CLI
# または GitHub の Actions タブから Run workflow

# ---------- ログ確認 ----------
gh run list --workflow=digest.yml                # 実行履歴
gh run view <RUN_ID> --log                       # ログ詳細
```

---

## 動作確認チェックリスト

- [ ] `git push` が成功すること
- [ ] GitHub Actions > Daily Digest ワークフローが表示されること
- [ ] 手動実行（Run workflow）が成功すること
- [ ] `docs/digests/` に `.md` と `.html` が生成されコミットされること
- [ ] `https://<user>.github.io/<repo>/` でアーカイブページが表示されること
- [ ] `https://<user>.github.io/<repo>/digests/` で最新ダイジェストが表示されること
- [ ] 翌朝 06:30 JST 以降に自動でワークフローが実行されること

---

## カスタマイズ

### フィードの追加/削除

[config/feeds.yml](config/feeds.yml) を編集するだけ:

```yaml
categories:
  AI_RESEARCH:
    feeds:
      - name: "新しいフィード"
        url: "https://example.com/feed.xml"
```

### ダイジェストのルール変更

[config/digest.yml](config/digest.yml) を編集:

```yaml
global:
  max_total_items: 20      # 記事数を増やす
  lookback_hours: 48       # 2日分取得
  summary_sentences: 4     # 要約文数を増やす
```

### 実行スケジュール変更

[.github/workflows/digest.yml](.github/workflows/digest.yml) の cron を変更:

```yaml
schedule:
  - cron: "0 22 * * *"    # 07:00 JST に変更
```

---

## トラブルシュート

### ワークフローが失敗する
```bash
# GitHub CLI でログ確認
gh run list --workflow=digest.yml --limit=5
gh run view <RUN_ID> --log-failed

# よくある原因:
# 1. フィードURLが無効 → config/feeds.yml を確認
# 2. Python依存のインストール失敗 → requirements.txt を確認
```

### ダイジェストが空になる
```bash
# ローカルで手動テスト
PYTHONPATH=src python -m digest_generator.run

# lookback_hours を広げてみる（config/digest.yml）
# フィードが実際に記事を配信しているか確認
curl -s "https://hnrss.org/best" | head -50
```

### GitHub Pages が表示されない
- Settings > Pages で Source が「GitHub Actions」になっているか確認
- Actions タブで deploy ジョブが成功しているか確認
- `docs/` ディレクトリにファイルがコミットされているか確認

### スケジュール実行されない
- GitHub Actions の cron はリポジトリが 60日間 活動がないと無効化される
- 定期的に push するか、手動で Actions を実行して活動を維持する
