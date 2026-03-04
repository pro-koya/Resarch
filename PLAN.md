あなたはSRE/DevOps + Pythonエンジニアです。
目的：OCI Always Free（ARM Ampere）Ubuntu VM 上に、Docker Compose で FreshRSS + PostgreSQL + updater + digest-generator + Caddy(HTTP) を構築し、「深く読むための高品質ソース収集」と「毎朝15分で読めるダイジェスト」を両立する。

重要前提：
- ドメインは取得しない（Let’s Encrypt/TLSは使わない）
- 公開はHTTPのみ（http://<PUBLIC_IP>/）
- CaddyはTLSではなく「リバースプロキシ + digest静的配信」に使う
- ARM環境（OCI Ampere）で動くこと
- データ取得元URL（フィードURL）は config/feeds.yml だけで自由に変更できること
- ダイジェストの“圧縮ルール”は config/digest.yml だけで自由に変更できること
- 無料運用が前提。LLM APIは必須にしない（P0は抽出要約で確実に動かす）
- ただし将来、スター記事だけLLM要約に切替できる拡張点は入れる（環境変数で差し替え可能）

------------------------------------------------------------
【最終的に実現したいUX】
------------------------------------------------------------
1) FreshRSS： http://<PUBLIC_IP>/ で閲覧できる
2) 毎朝の要約： http://<PUBLIC_IP>/digests/latest で閲覧できる（Markdownをそのまま表示 or テキスト表示でOK）
3) Deep Reading（週末1時間）：FreshRSSでスター（⭐）を付ける運用
4) Morning Digest（15分）：基本は「スター記事＋カテゴリ未読上位」だけを対象に、短くまとめる

------------------------------------------------------------
【アーキテクチャ要件（P0）】
------------------------------------------------------------
- docker compose v2
- services:
  - caddy (HTTP only)
  - freshrss (official image freshrss/freshrss)
  - postgres (official image)
  - updater (cron container) : 20分間隔で actualize_script.php を実行
  - digest-generator (python) : 毎朝 06:30 JST に digest 生成
  - digest-cron (cron container) : digest-generator を定期実行（コンテナ内cron）
- 永続化:
  - ./data (FreshRSS)
  - ./pgdata (Postgres)
  - ./digests (digest出力)
  - ./backups (バックアップ)
  - caddyのdata/config
- restart policy: unless-stopped
- logging: json-file の max-size/max-file を全サービスに設定し、ログ肥大化を防ぐ
- セキュリティ:
  - OCI側で 22/80 のみ開放（80のみ公開。5432等は公開しない）
  - Ubuntu側で ufw の推奨設定も提示
  - SSH鍵のみの推奨設定も提示（root login禁止など）

------------------------------------------------------------
【情報ソース管理要件】
------------------------------------------------------------
A) config/feeds.yml
- FreshRSSに登録するフィードをカテゴリ別に宣言的に管理
- 変更はこのファイルだけでOK
- 初回起動時に自動登録（or 1コマンドで登録）
- 追加/削除/カテゴリ変更が再実行で反映される（差分更新）

B) config/digest.yml
- “毎朝要約の対象とルール”を宣言的に管理
- 例：各カテゴリ最大件数、スター優先、未読上位、要約方法（extractive/llm）など

------------------------------------------------------------
【Digest生成要件（重要）】
------------------------------------------------------------
- 生成物： ./digests/YYYY-MM-DD.md と ./digests/latest.md
- Digest構造（必須）：
  - Header: 日付、生成時刻、対象範囲
  - Section: AI_RESEARCH / AI_PRODUCT_SAAS / MACRO_STRUCTURE / JAPAN_SIGNAL / AGRICULTURE
  - 各記事：タイトル、出典、URL、要約（2〜4行）、転用示唆（1行：本業/個人開発/農業のいずれか）、次アクション（任意1行）
- 15分で読める分量制限：
  - 合計最大 12〜15件
  - 各カテゴリ max_items は digest.yml で指定
- 要約方法（P0）：
  - Python抽出要約（TextRank相当 or シンプル頻度ベースでOK）
  - “洞察”は要約に混ぜない。転用示唆はルールベースで短く（または空でも良い）
- 拡張点（P1）：
  - SUMMARIZER=llm の場合だけ外部API要約を使用可能に（デフォルトは extractive）
  - APIキー等は .env で管理し、未設定なら自動で extractive にフォールバック

------------------------------------------------------------
【FreshRSSからの取得方法】
------------------------------------------------------------
- FreshRSSの外部API（Fever API または Google Reader API）を使用して記事一覧を取得する。
- 実装は「APIクライアント層」を作り、どちらのAPIでも差し替えできる設計にする。
- 取得対象は digest.yml のポリシーに従う（例：starred_first / unread_top）
- 本文取得はP0はRSS本文（content/summary）優先。記事URLのスクレイピングはP0では必須にしない（壊れやすいので）。

------------------------------------------------------------
【バックアップ要件】
------------------------------------------------------------
- scripts/backup.sh を作成
- 日次 03:30 JST に実行（cronコンテナでOK）
- 内容：
  - Postgres: pg_dump（圧縮）
  - FreshRSS data/: tar.gz
  - digests/: tar.gz（任意）
- 世代管理：7日分（古いものから削除）
- ディスク使用量の簡易チェック（閾値超過で古い順に削除 or 警告ログ）

------------------------------------------------------------
【出力してほしい成果物】
------------------------------------------------------------
1) 推奨ディレクトリ構成（/srv/rss/ 配下想定）
2) docker-compose.yml（完全版）
3) Caddyfile（HTTPのみ、/ は freshrss へ reverse_proxy、/digests/* は ./digests を静的配信）
4) config/feeds.yml サンプル（海外/日本を混ぜた高品質ソースを少数精鋭で）
5) config/digest.yml サンプル（スター優先＋未読上位のルール）
6) scripts/import_feeds.py（または .sh）：
   - feeds.yml を読み、FreshRSSにフィード登録/差分更新
   - 認証情報は .env から取得
7) digest-generator の実装一式（Python）：
   - src/ 配下に配置
   - APIクライアント層、取得ロジック、要約ロジック、Markdown生成、I/O
   - 実行コマンド：python -m digest_generator.run
8) cron設定（updater / digest / backup をコンテナで回す）
9) Ubuntu初期セットアップ手順（コマンドを順番に）
10) OCI GUI操作手順（ARMインスタンス作成、VCN、Security List/NSG、パブリックIP確認）
11) 動作確認チェックリスト
    - FreshRSSが開ける
    - /digests/latest が見える
    - updaterが動いて記事が増える
    - digestが毎朝生成される
    - backupが生成される
12) トラブルシュート集（OCI FW/UFW、Caddy、DB接続、cron動いてない、ディスク枯渇）

------------------------------------------------------------
【制約/注意】
------------------------------------------------------------
- “ドメイン無し”なのでTLSは構成に含めない（CaddyはHTTPのみ）
- 外部有料SaaSは使わない
- secretsは .env に置き、サンプルは .env.example として出す（本番値は書かない）
- すべてMarkdownで、コードはコードブロックで提示する
- プレースホルダは <PUBLIC_IP>, <FRESHRSS_ADMIN_USER>, <FRESHRSS_ADMIN_PASS> のように明確にする
- ARM互換を意識し、x86専用イメージは避ける（official images優先）

まず「設計方針（なぜこうするか）」を短く説明し、その後に全ファイル内容・手順を提示してください。
最後に「最小実行コマンド集（コピペ用）」をまとめてください。