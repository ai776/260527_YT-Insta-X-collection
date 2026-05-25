---
name: sales-list-collect
description: >
  著者名リストが入ったGoogleスプレッドシートを受け取り、
  SNS・メール・問い合わせフォーム・HP・ブログを自動収集してO〜AA列に書き込む。
  Serper.dev（Google検索）＋HPスクレイピング＋YouTubeブラウザ操作の3段階で取得。
tags:
  - sales
  - scraping
  - google-sheets
---

# sales-list-collect — 営業リスト自動収集

著者名リストから SNS・連絡先情報を自動収集し、Google スプレッドシートに書き込むスキル。

## Inputs / Outputs

- **In:** Google スプレッドシートID（I列に著者名が入っているもの）
- **Out:** O〜AA列に収集結果を書き込み（メール・問い合わせ・HP・ブログ・YouTube・Twitter・Facebook・Instagram）

## 対象スプレッドシート

ID: `1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg`
対象シート: ビジネス書 / スピリチュアル・自己啓発 / 教養・雑学 / 生活・実用書

| 列 | 収集内容 |
|----|---------|
| O  | メールアドレス |
| P  | 問い合わせページURL |
| Q  | 会社HP・公式サイト |
| R  | ブログ（ameba/note/はてな等） |
| S  | YouTube チャンネル |
| U  | Twitter/X |
| X  | Facebook |
| Z  | Instagram |

## ワークフロー

### Step 1: SNS・HP・メール・ブログの一括収集

```bash
source ~/.bash_profile

# テスト（3件）
python3 main.py --sheet-id <SHEET_ID> --limit 3

# 特定行だけ上書き確認
python3 main.py --sheet-id <SHEET_ID> --row 2 --overwrite

# 全件実行
python3 main.py --sheet-id <SHEET_ID>
```

処理内容（1人あたり最大3 APIリクエスト）:
1. Serper.dev で X/Facebook/YouTube/Instagram を個別検索
2. HP トップページを検索 → スクレイピングでメール・問い合わせフォーム抽出
3. ブログ（ameba/note/はてな等）を検索
4. メールが見つからない場合は Google スニペットから取得

途中停止しても再実行すれば未入力行から続行する。

### Step 2: YouTube ブラウザ操作でメール確認・補完

O列（メール）が空でS列（YouTube）がある行を対象にブラウザ操作でメールを取得する。
**Claude Code セッション内（Claude-in-Chrome が使える状態）で実行すること。**

対象URL一覧の確認:
```bash
source ~/.bash_profile
python3 youtube_email_batch.py --sheet-id <SHEET_ID> --limit 20
```

1チャンネルあたりの手順:
1. `https://www.youtube.com/@{handle}/about` を開く
2. JS実行: `document.querySelector('#description-container #expand')?.click()`
3. モーダルが開く → 下にスクロール
4. 「メールアドレスの表示」ボタンがある場合:
   - ボタンをクリック
   - reCAPTCHA チェックボックスをクリック → 「送信」
   - メールアドレスが表示 → O列に書き込む
5. ボタンがない場合: スキップ（メール非公開）

O列への書き込み:
```python
from sheets import _service
svc = _service()
svc.values().update(
    spreadsheetId="<SHEET_ID>",
    range="{シート名}!O{行番号}",
    valueInputOption="RAW",
    body={"values": [["メールアドレス"]]},
).execute()
```

## 環境・前提条件

| 項目 | 内容 |
|------|------|
| 環境変数 | `SERPER_KEY`（~/.bash_profile に設定済み） |
| 認証ファイル | `credentials.json`（プロジェクトフォルダに配置） |
| シート共有 | `id-60525-sns-collection@sns-collection-497403.iam.gserviceaccount.com` に編集者権限 |
| YouTube操作 | Claude Code + Claude-in-Chrome MCP が必要 |

## コスト

- Serper.dev 無料枠 2,500件/月 → 約 800〜1,200 人分処理可能
- YouTube ブラウザ操作は無料（時間コストのみ）

## 注意事項

- Q列（HP）に問い合わせページが入らないよう除外済み（`inquir` / `contact` / `/form` を含むURLはQに入らない）
- URLの `#アンカー` は自動除去される
- このツールは Claude Code 環境が必要なため他者への配布は不可（YouTube ブラウザ操作のため）
