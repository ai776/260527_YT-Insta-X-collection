# 営業リスト自動収集ツール

著者名リストから SNS・メール・問い合わせフォームを自動収集し、Google スプレッドシートに書き込む。

## 環境変数（~/.bash_profile に設定済み）

```bash
export SERPER_KEY="..."         # Serper.dev APIキー（無料2,500件/月）
```

## ファイル構成

```
main.py                  # メイン実行スクリプト
youtube_email_batch.py   # YouTube ブラウザ操作バッチ（対象URL一覧出力）
setup_sheets.py          # スプレッドシート初期セットアップ
models.py                # PersonRecord データクラス
sheets.py                # Google Sheets 読み書き（credentials.json を使用）
searcher.py              # Serper.dev で SNS URL・メール検索
scrapers/
  hp_scraper.py          # HP スクレイピング（メール・問い合わせフォーム抽出）
  youtube_browser.py     # YouTube ブラウザ操作のユーティリティ
credentials.json         # Google サービスアカウントキー（要共有設定）
```

## スプレッドシート構成

対象スプレッドシートID: `1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg`

対象シート: ビジネス書 / スピリチュアル・自己啓発 / 教養・雑学 / 生活・実用書

| 列 | 内容 |
|----|------|
| I  | 著者名（入力元） |
| O  | メールアドレス |
| P  | 問い合わせページ |
| Q  | HP |
| S  | YouTube |
| U  | Twitter/X |
| X  | Facebook |
| Z  | Instagram |

## 実行手順

### Step 1: SNS・メール・フォームの自動収集

```bash
source ~/.bash_profile

# テスト（3件）
python3 main.py --sheet-id 1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg --limit 3

# 全件
python3 main.py --sheet-id 1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg

# 特定行だけ上書き（行番号はシート上の番号）
python3 main.py --sheet-id 1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg --row 2 --overwrite
```

処理内容（1人あたり最大2 APIリクエスト）:
1. Serper.dev で X/Facebook/YouTube/Instagram を個別検索
2. HP を検索して scrape（メール・問い合わせフォームを抽出）
3. メールが見つからない場合は Google 検索スニペットから取得
4. 途中停止しても再実行すると未入力行から続行

### Step 2: YouTube「メールアドレスの表示」でメール確認・補完

O列（メール）が空でS列（YouTube）がある行に対してブラウザ操作で取得する。  
**Claude Code のセッション内（Claude-in-Chrome が使える状態）で実行すること。**

#### 対象URLの確認
```bash
source ~/.bash_profile
python3 youtube_email_batch.py --sheet-id 1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg --limit 20
```

#### ブラウザ操作手順（1チャンネルあたり）

1. `https://www.youtube.com/@{handle}/about` を開く
2. JS実行: `document.querySelector('#description-container #expand')?.click()`
3. モーダルが開く → 下にスクロール
4. 「メールアドレスの表示」ボタンが**ある場合**:
   - ボタンをクリック
   - reCAPTCHA のチェックボックスをクリック
   - 「送信」ボタンをクリック
   - メールアドレスが表示される → O列に書き込む
5. ボタンが**ない場合**: スキップ（そのチャンネルはメール非公開）

#### シートへの書き込み
```python
from sheets import _service
svc = _service()
svc.values().update(
    spreadsheetId="1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg",
    range="ビジネス書!O{行番号}",
    valueInputOption="RAW",
    body={"values": [["取得したメールアドレス"]]},
).execute()
```

## コスト感

| 処理 | 消費 |
|------|------|
| SNS一括検索 | Serper 1件/人 |
| HP追加検索（SNSでHPが見つからない場合） | Serper +1件/人 |
| HP/問い合わせページ スクレイピング | 無料 |
| YouTube ブラウザ操作 | 無料（時間コストのみ） |

Serper 無料枠 2,500件 → 約 1,250〜2,500 人分処理可能

## 注意事項

- `credentials.json` はプロジェクトフォルダに置くだけでよい（環境変数不要）
- スプレッドシートはサービスアカウント `id-60525-sns-collection@sns-collection-497403.iam.gserviceaccount.com` に編集者権限で共有すること
- YouTube ブラウザ操作は Claude Code（Claude-in-Chrome MCP）が必要なため、他者への配布は不可
- 中断した場合は同じコマンドを再実行すれば未入力行から続行する
