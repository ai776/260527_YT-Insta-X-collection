# 営業リスト自動収集ツール

著者名リスト（Google スプレッドシートのI列）から、SNS・メール・問い合わせフォーム・HP・ブログを自動収集してO〜AA列に書き込むツール。

Serper.dev（Google検索API）＋HPスクレイピング＋Claude-in-Chrome ブラウザ操作＋サブエージェントによる本人特定 の4要素を組み合わせる。

---

## 1. セットアップ（環境設定）

### 1.1 必要なもの

| 項目 | 用途 |
|---|---|
| Python 3.10+ | スクリプト実行 |
| Google Cloud サービスアカウント | スプレッドシート読み書き |
| Serper.dev APIキー | Google検索（無料2,500件/月） |
| Claude Code + Claude-in-Chrome MCP | ブラウザ操作（フォロワー数等） |

### 1.2 GCP サービスアカウント作成

1. https://console.cloud.google.com/ で新規プロジェクト作成
2. 「APIとサービス」→「ライブラリ」で **Google Sheets API** を有効化
3. 「IAMと管理」→「サービスアカウント」で新規作成
4. 作成後、サービスアカウント詳細 →「キー」→「鍵を追加」→ JSON形式でダウンロード
5. ダウンロードしたJSONをプロジェクト直下に `credentials.json` として配置
6. JSON内の `client_email`（例: `id-60525-sns-collection@sns-collection-497403.iam.gserviceaccount.com`）を控える

### 1.3 スプレッドシート共有

対象スプレッドシートを開き、右上「共有」から **`client_email` を編集者権限で追加**。
これを忘れると `403 Permission denied` で読み書き失敗する。

### 1.4 Serper.dev APIキー

1. https://serper.dev/ にサインアップ
2. ダッシュボードでAPIキー取得
3. `~/.bash_profile` に追記:

   ```bash
   export SERPER_KEY="ここにAPIキー"
   ```

4. `source ~/.bash_profile` を実行（または新しいシェルを開く）

### 1.5 Python依存パッケージ

```bash
pip install google-api-python-client google-auth requests beautifulsoup4
```

### 1.6 ディレクトリ初期化

```bash
mkdir -p staging verifications
```

`staging/` `verifications/` は実行時にも自動作成されるが、手動で作っておくと安心。

### 1.7 動作確認

```bash
source ~/.bash_profile
python3 main.py --sheet-id <スプレッドシートID> --row 2 --overwrite
```

`staging/{シート名}_2.json` が生成され、シートのN2セルに `⚠️未検証` が入れば成功。

---

## 2. 必須ワークフロー（3段階・厳守）

main.py は本番列(O〜AA)に直接書き込まない。**必ず以下の3段階を通すこと。**
この設計の理由は §5「なぜ3段階に分けるか」を参照。

### Stage 1: 自動収集

```bash
source ~/.bash_profile

# 特定行のみ
python3 main.py --sheet-id <ID> --row N --overwrite

# テスト（3件）
python3 main.py --sheet-id <ID> --limit 3

# 全件
python3 main.py --sheet-id <ID>
```

処理内容（1人あたり最大3 APIリクエスト）:
1. Serper.dev で X/Facebook/YouTube/Instagram を個別検索
2. HP トップページを検索 → スクレイピングでメール・問い合わせフォーム抽出
3. ブログ（ameba/note/はてな等）を検索
4. メールが見つからない場合は Google スニペットから取得

結果は `staging/{シート名}_{行番号}.json` に保存。N列に `⚠️未検証` マーカーのみ書き込まれる。

### Stage 2: サブエージェント検証 ＋ ブラウザでフォロワー数取得

**Claude Code セッション内で実施。** Stage 1の値が"それらしく見える"場合でも省略しない。

#### サブエージェント本人特定（Claude が `general-purpose` agent を呼ぶ）

指示テンプレート:

```
著者「{著者名}」（{ジャンル}）について本人を特定し以下を返してください。
背景: 自動収集で以下が取れたが要検証
- X: {自動収集値}
- YT: {自動収集値}
- Mail: {自動収集値}
- Form: {自動収集値}

調査:
1. Amazon等で著作を検索し、本人プロフィール・所属を特定
2. 公式HPを特定し WebFetch で確認
3. 以下のURLを返す:
   - O メール / P 問い合わせ / Q HP / R ブログ
   - S YouTube (@handle/featured) / U X / X Facebook / Z Instagram
4. 各URLが実在し本人公式であることを WebSearch/WebFetch で確認
特定不可なら明記。300語以内。
```

#### ブラウザでフォロワー数取得（Claude-in-Chrome）

| 対象 | 取得方法 |
|---|---|
| YouTube登録者数 (T) | `/about` を開き `チャンネル登録者数\s*([\d.,]+\s*[万千億]?(?:\s*人)?)` をJSで抽出 |
| YouTubeメール (O) | `/about` →「メールアドレスの表示」→ reCAPTCHA → 送信 |
| Xフォロワー (V) | プロフィール開いて `([\d.,]+\s*[万千億]?)\s*フォロワー` |
| XのDM有無 (W) | `[data-testid="sendDMFromProfile"]` の存在 |
| Facebookフォロワー (Y) | プロフィール開いて `フォロワー([\d,.]+)人` |
| Instagramフォロワー (AA) | `meta[name=description]` から `フォロワー([\d,.KM]+)人` |

補助スクリプトで「ブラウザ取得が必要な行」の一覧を出せる:

```bash
python3 youtube_subs_batch.py --sheet-id <ID> --limit 20   # T列が空の対象
python3 youtube_email_batch.py --sheet-id <ID> --limit 20  # O列が空でS列あり
python3 x_followers_batch.py --sheet-id <ID> --limit 20    # V列が空でU列あり
```

#### 検証ログの保存（必須）

調査結果を必ず `verifications/{シート名}_{行番号}.md` に保存する。
ファイルが無いと Stage 3 の `promote.py` が **昇格失敗**する（技術的ガード）。

### Stage 3: 本番列へ昇格

```bash
python3 promote.py --sheet-id <ID> --sheet "ビジネス書" --row N --verified \
  --set Q="https://example.com/" \
  --set R="https://example.com/blog" \
  --set S="https://www.youtube.com/@handle/featured" \
  --set T="2.89万" \
  --set U="https://x.com/handle" --set V="47.8万" \
  --set X="https://www.facebook.com/handle/" --set Y="123" \
  --set Z="https://www.instagram.com/handle/" --set AA="11.7万" \
  --n-note "備考があれば記載"
```

- `--verified` フラグ必須
- `verifications/*.md` 存在チェック
- ステージングJSONの値 + `--set` 上書きでO〜AA列に一括書き込み
- N列の `⚠️未検証` を `--n-note` の内容に置換（指定なしならクリア）

### Stage 4: 参照シートと比較（推奨）

```python
from sheets import _service
svc = _service()
ref_id = "1US8ucThOaxWvI9oxnmA0yXx0lmYxT4VYdGS2AW7tKys"
cur_id = "<対象ID>"
for sid, label in [(ref_id, "REF"), (cur_id, "CUR")]:
    r = svc.values().get(spreadsheetId=sid, range="ビジネス書!A<行>:AA<行>") \
            .execute().get("values", [[]])[0]
    print(label, r)
```

---

## 3. スプレッドシート列定義

| 列 | 内容 | 取得方法 |
|---|---|---|
| I | 著者名（入力） | 手動入力 |
| J | 著者URL（入力） | 手動入力 |
| N | 備考 / `⚠️未検証` マーカー | main.py / promote.py |
| O | メールアドレス | HPスクレイピング / YouTube概要欄 / Facebook基本データ |
| P | 問い合わせフォームURL | HPスクレイピング |
| Q | 会社HP・公式サイト | Serper検索 → サブエージェント検証 |
| R | ブログ（HP内blog / ameba / note 等） | Serper検索 ※公式HP内blogを優先 |
| S | YouTubeチャンネル（`@handle/featured` 形式に統一） | Serper検索 → ブラウザ確認 |
| T | YouTube登録者数 | ブラウザ操作 |
| U | X/Twitter | Serper検索 → サブエージェント検証 |
| V | Xフォロワー数 | ブラウザ操作 |
| W | XのDM有無 (TRUE/FALSE) | ブラウザ操作 |
| X | Facebook | Serper検索 → サブエージェント検証 |
| Y | Facebookフォロワー数 | ブラウザ操作 |
| Z | Instagram | Serper検索 |
| AA | Instagramフォロワー数 | ブラウザ操作 |

---

## 4. ファイル構成

```
main.py                  # Stage 1: 自動収集 → staging/
promote.py               # Stage 3: 検証完了後に本番列へ昇格
models.py                # PersonRecord データクラス
searcher.py              # Serper.dev API ラッパー
sheets.py                # Google Sheets API ラッパー
scrapers/
  hp_scraper.py          # HPスクレイピング（メール・フォーム抽出）
  youtube_browser.py     # YouTube ブラウザ操作ユーティリティ
youtube_email_batch.py   # O列補完対象の列挙
youtube_subs_batch.py    # T列補完対象の列挙
x_followers_batch.py     # V列補完対象の列挙
setup_sheets.py          # スプレッドシート初期セットアップ
staging/                 # ステージングJSON（main.py出力、gitignore）
verifications/           # 検証ログ（必須、gitignore）
credentials.json         # GCPサービスアカウントキー
.claude/skills/sales-list-collect/SKILL.md  # 詳細ワークフロー
CLAUDE.md                # Claude Code向け運用ルール
```

---

## 5. なぜ3段階に分けるか（設計理由）

自動収集の結果は "URL形式は正しい" が "中身は別人" のケースが頻発する。実際に観測された誤マッチ事例:

| 著者 | 自動取得値 | 実際 |
|---|---|---|
| コンプライアンス研究会 | `contact@minatolaw.com`（湊法律事務所） | 弁護士有志ユニット、独立SNSなし |
| 村中 一英 | `intel@kyokyo-u.ac.jp`（京都教育大） | 社労士法人ガーディアン代表 |
| 伊藤塾 (X3) | `facebook.com/itoujuku/`（小学校学習塾） | `facebook.com/itojuku.zaitaku/` が正解 |
| U6 | `@takaramap`（別人FP） | `@reikijapan` |
| X10 | `@akinori_0226`（別人） | `@kanagawa_Aki` |

これらは**形式の正しさで本人と錯覚する確証バイアス**を排除しない限り再発する。
対策として、main.py の出力を一旦ステージングに退避し、サブエージェントによる「Amazon→著者プロフィール→公式」の**逆引き検証ログ**が存在する場合のみ本番列に反映する設計とした。

### サブエージェント検証が抜ける原因（既知）

1. **確証バイアス**: URL形式が整っていると本人と思い込む
2. **例外処理として誤分類**: 「怪しい時だけ呼ぶ」と無意識に分類してしまう
3. **コスト最適化の暴走**: サブエージェントは高コストなので「不要そう」と省略
4. **行ごとに文脈リセット**: 前行の失敗教訓を忘却し「今回は単純そう」と再判断
5. **同名別人の頻度過小評価**: 繰り返し失敗しているのに希望的観測で再発
6. **受動性**: ユーザー指摘待ち。本来は無条件で疑うべき

### 強制ゲート

- `main.py` は staging にしか書かない（本番列に直接書けない）
- `promote.py` は `--verified` フラグ + `verifications/*.md` が無いと停止
- N列に `⚠️未検証` が残る = 検証未完了がシート目視で分かる

---

## 6. よくある間違いと対処

### O列（メール）が空になる
**原因**: main.py はYouTubeの「メールアドレスの表示」機能を使わない。サブエージェントのWeb検索でも非公開のため発見不可。
**対処**: S列にYouTubeがある行は **youtube_email_batch.py で対象URLを列挙→ブラウザでメール表示ボタン経由で取得**。

### O列（メール）がHPフッターに載っているのに取得できない
**原因**: `hp_scraper.py` のスクレイピングがフッター部分のメールを取得できないことがある。
**対処**: 公式HPのトップページフッターを目視確認、または以下で直接抽出:

```python
import re, requests
html = requests.get("https://公式HP").text
emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html)
print([e for e in emails if "example" not in e])
```

### R列（ブログ）で外部ブログサービスを優先してしまう
**原因**: サブエージェント指示が曖昧だと ameba/note を HP内blog より優先する。
**対処**: 「公式HP内のブログ（/blog等）がある場合はそちらを優先」とプロンプトに明示。公式HPのblogリンクをWebFetchで確認。

### S列（YouTube URL）がチャンネルIDベースになる
**原因**: Serperが `/channel/UC...` 形式で返すことがある。
**対処**: `@ハンドル名/featured` 形式に統一（チャンネルページのアドレスバーで確認）。

### X列（Facebook）で法人ページと個人ページを混同する
**対処**:
- X列には**本人確認できるページ**（経歴・所在地・投稿内容が一致）
- 公式ページと個人プロフィール両方ある場合 → 公式をX列、個人をN列備考に `Facebook個人アカウント: {URL}`
- フォロワー数が極端に少ない/所在地違いは別物

### YouTubeチャンネルが版元（KADOKAWA等）の出版社チャンネルだった
**判断**: 本人個人チャンネルがなくても、著者出演の主要発信媒体ならS列に入れる（村中一英 → @eiseikanri 等）。ただし検証ログに「本人運営ではないが主要発信媒体」と明記。

---

## 7. コスト・制限

- Serper.dev 無料枠: 2,500件/月 → 約 800〜1,200 人分処理可能
- ブラウザ操作（Claude-in-Chrome）: 無料、時間コストのみ
- サブエージェント: トークンコスト発生（行ごとに数千〜1万トークン程度）

---

## 8. 注意事項

- `credentials.json` は機密。git管理しない（`.gitignore` 推奨）
- スプレッドシートは GCP サービスアカウントの `client_email` に編集者権限で共有必須
- このツールは Claude Code 環境（Claude-in-Chrome MCP使用）が前提のため、他者への配布不可
- 中断した場合は同じコマンドを再実行すれば未入力行から続行する（`--overwrite` なしの場合）
