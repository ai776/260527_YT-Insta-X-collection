# 営業リスト自動収集ツール

著者名リストから SNS・メール・問い合わせフォームを自動収集し、Google スプレッドシートに書き込む。

## ⚠️ 必須ルール（厳守）

**各行を処理する際は必ず次の順序で実行すること:**

1. `main.py --row N --overwrite` で自動収集
2. **サブエージェント(general-purpose)で本人特定 & 全URL検証**（怪しいかどうかに関わらず**必ず**実行）
   - Amazonで著作→著者プロフィール→公式 の逆引きで特定
   - 自動収集の値が"それらしく見える"だけで本人と判断しない
   - 同名別人・別組織への誤マッチ事例多数（X3/U6/X10/コンプライアンス研究会等）
3. ブラウザ(Claude-in-Chrome)で各SNSフォロワー数を取得（T/V/Y/AA列）
4. シートに最終書き込み
5. 参照シート `1US8ucThOaxWvI9oxnmA0yXx0lmYxT4VYdGS2AW7tKys` と比較

詳細は `.claude/skills/sales-list-collect/SKILL.md` の「最重要ワークフロー」を参照。

### 2段階書き込みアーキテクチャ（厳守）

**main.py は本番列(O〜AA)に直接書き込まない。** ステージングJSON + N列マーカーのみ更新する。

#### Stage 1: 自動収集
```bash
python3 main.py --sheet-id <ID> --row N --overwrite
```
- `staging/{シート名}_{行番号}.json` に収集結果を保存
- 対象行のN列に `⚠️未検証` を書き込み（シート目視で進捗確認可能）
- **O〜AA列には何も書かれない**

#### Stage 2: サブエージェント検証
- general-purpose サブエージェントで本人特定・URL検証を実施
- 結果を `verifications/{シート名}_{行番号}.md` に必ず保存
- ブラウザ(Claude-in-Chrome)で各SNSのフォロワー数を取得

#### Stage 3: 昇格（本番反映）
```bash
python3 promote.py --sheet-id <ID> --sheet "ビジネス書" --row N --verified \
  --set T="2.89万" --set V="47.8万" --set AA="11.7万" \
  --n-note "備考があれば記載"
```
- `--verified` フラグ必須（検証完了の明示）
- `verifications/*.md` が存在しないと昇格失敗（技術的ガード）
- ステージングJSONの値 + `--set` 上書きでO〜AA列に書き込み
- N列の `⚠️未検証` マーカーをクリア（または `--n-note` の備考に置換）

**この経路を通らずに本番列に直接書き込むことは禁止。** どうしても直接書く必要がある場合（例: ステージングが破損）も、必ずサブエージェント検証ログを残してから書くこと。

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
