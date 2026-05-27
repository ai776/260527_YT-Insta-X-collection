# 営業リスト自動収集ツール

著者名リストから SNS・メール・問い合わせフォームを自動収集し、Google スプレッドシートに書き込む。

## ⚠️ 必須ルール（厳守）

**各行を処理する際は必ず次の順序で実行すること:**

1. **サブエージェント(general-purpose)で本人特定 & 連絡先調査**（WebSearch+WebFetch）
   - Amazonで著作→著者プロフィール→公式 の逆引きで特定
   - 同名別人・別組織への誤マッチ事例多数（X3/U6/X10/コンプライアンス研究会等）
2. 検証ログを `verifications/{シート名}_{行番号}_{ハンドル}.md` に保存（confidence + evidence）
3. ブラウザ(Claude-in-Chrome)で各SNSフォロワー数を取得（T/V/Y/AA列）
4. シートに書き込み（O〜AA列 + N列備考）
5. 参照シート `1US8ucThOaxWvI9oxnmA0yXx0lmYxT4VYdGS2AW7tKys` と比較

詳細は `.claude/skills/sales-list-collect/SKILL.md` を参照。

> ⚠️ **Serper.dev は2026-05に廃止しました。** 旧 `main.py` `searcher.py` も削除済み。  
> 同名別人の誤マッチが頻発したため、サブエージェントによる本人特定方式に統一。

### サブエージェント検証は必須
- 検証ログ `verifications/*.md` を必ず残す（confidence/evidence 記載）
- ログなしで本番列(O〜AA)に書き込むのは禁止

## ファイル構成

```
youtube_email_batch.py   # YouTube ブラウザ操作バッチ（対象URL一覧出力）
youtube_subs_batch.py    # YouTube 登録者数バッチ
x_followers_batch.py     # X フォロワー数バッチ
setup_sheets.py          # スプレッドシート初期セットアップ
models.py                # PersonRecord データクラス
sheets.py                # Google Sheets 読み書き（credentials.json を使用）
scrapers/
  hp_scraper.py          # HP スクレイピング（メール・問い合わせフォーム抽出）
  youtube_browser.py     # YouTube ブラウザ操作のユーティリティ
credentials.json         # Google サービスアカウントキー（要共有設定）
verifications/           # サブエージェント検証ログの保存先
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

### Step 1: SNS・メール・HPをサブエージェントで調査

各人物につき `general-purpose` サブエージェントを起動し、WebSearch+WebFetchで本人特定→公式情報を取得する。詳細テンプレートは `.claude/skills/sales-list-collect/SKILL.md` 参照。

並列実行可能（5〜10体推奨）。1人あたり~30秒・誤マッチほぼゼロ。結果は `verifications/*.md` に保存。

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

### Step 3: YouTubeチャンネル登録者数をブラウザで取得（T列補完）

T列（登録者数）が空でS列（YouTube）がある行に対してブラウザ操作で取得する。  
**Claude Code のセッション内（Claude-in-Chrome が使える状態）で実行すること。**

#### 対象URLの確認
```bash
source ~/.bash_profile
python3 youtube_subs_batch.py --sheet-id 1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg --limit 20
```

#### ブラウザ操作手順（1チャンネルあたり）

1. 対象URLをブラウザで開く
2. JS実行でページテキストから登録者数を取得:
   ```javascript
   document.body.innerText.match(/チャンネル登録者数\s*([\d.,]+\s*[万千億]?(?:\s*人)?)/)?.[1]
   ```
3. 取得できた値を T列に書き込む

#### シートへの書き込み
```python
from sheets import _service
svc = _service()
svc.values().update(
    spreadsheetId="1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg",
    range="ビジネス書!T{行番号}",
    valueInputOption="RAW",
    body={"values": [["5.6万"]]},
).execute()
```

## コスト感

| 処理 | 消費 |
|------|------|
| サブエージェント本人特定 | 1人あたり~30秒（並列可） |
| HP/問い合わせページ スクレイピング | 無料 |
| YouTube/X/Facebook/Instagram ブラウザ操作 | 無料（時間コストのみ） |

## 注意事項

- `credentials.json` はプロジェクトフォルダに置くだけでよい（環境変数不要）
- スプレッドシートはサービスアカウント `id-60525-sns-collection@sns-collection-497403.iam.gserviceaccount.com` に編集者権限で共有すること
- YouTube ブラウザ操作は Claude Code（Claude-in-Chrome MCP）が必要なため、他者への配布は不可
- 中断した場合は同じコマンドを再実行すれば未入力行から続行する
