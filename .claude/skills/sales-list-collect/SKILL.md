---
name: sales-list-collect
description: >
  著者名リストが入ったGoogleスプレッドシートを受け取り、
  SNS・メール・問い合わせフォーム・HP・ブログを自動収集してO〜AA列に書き込む。
  Serper.dev（Google検索）＋HPスクレイピング＋各SNSブラウザ操作の4段階で取得。
tags:
  - sales
  - scraping
  - google-sheets
---

# sales-list-collect — 営業リスト自動収集

著者名リストから SNS・連絡先情報を自動収集し、Google スプレッドシートに書き込むスキル。

## Inputs / Outputs

- **In:** Google スプレッドシートID（I列に著者名が入っているもの）
- **Out:** O〜AA列に収集結果を書き込み

## 対象スプレッドシート

ID: `1tP78UIB4BNby6bUdvI38OqrhoijdOx7GZJXLYDuuIAg`
対象シート: ビジネス書 / スピリチュアル・自己啓発 / 教養・雑学 / 生活・実用書

| 列 | 収集内容 | 取得方法 |
|----|---------|---------|
| O  | メールアドレス | HPスクレイピング / Googleスニペット / Facebook / YouTube |
| P  | 問い合わせページURL | HPスクレイピング |
| Q  | 会社HP・公式サイト | Serper検索 |
| R  | ブログ（ameba/note/はてな等） | Serper検索 |
| S  | YouTube チャンネル | Serper検索 |
| T  | YouTube 登録者数 | ブラウザ操作（`youtube_subs_batch.py`） |
| U  | Twitter/X | Serper検索 |
| V  | Twitterフォロワー数 | ブラウザ操作（`x_followers_batch.py`） |
| W  | TwitterDM有無 | ブラウザ操作（XプロフィールJS） |
| X  | Facebook | Serper検索 ※非公式ページに注意、目視確認推奨 |
| Y  | Facebookフォロワー数 | ブラウザ操作（Facebookページ） |
| Z  | Instagram | Serper検索 |
| AA | Instagramフォロワー数 | ブラウザ操作（Instagramページ） |

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

> ⚠️ **Step 1完了後は必ずStep 2とStep 2.5を実行すること。**  
> S列にYouTube URLがある著者のO列メールはStep 1では取得できない。  
> Step 2.5（youtube_email_batch.py）をスキップするとO列が永久に空のままになる。

### Step 2: YouTube 登録者数をブラウザで取得（T列）

S列（YouTube URL）があり T列が空の行を対象。  
**Serperスニペットは精度が低いためブラウザ取得のみ。**  
**Claude Code セッション内（Claude-in-Chrome が使える状態）で実行すること。**

対象URL一覧の確認:
```bash
source ~/.bash_profile
python3 youtube_subs_batch.py --sheet-id <SHEET_ID> --limit 20
```

1チャンネルあたりの手順:
1. 対象チャンネルURLをブラウザで開く
2. JSで登録者数を取得:
   ```javascript
   document.body.innerText.match(/チャンネル登録者数\s*([\d.,]+\s*[万千億]?(?:\s*人)?)/)?.[1]
   ```
3. T列に書き込む:
   ```python
   svc.values().update(spreadsheetId="<SHEET_ID>", range="{シート名}!T{行番号}",
       valueInputOption="RAW", body={"values": [["5.6万"]]}).execute()
   ```

### Step 2.5: YouTube メール確認・補完（O列）

O列（メール）が空でS列（YouTube）がある行を対象。

対象URL一覧の確認:
```bash
python3 youtube_email_batch.py --sheet-id <SHEET_ID> --limit 20
```

1チャンネルあたりの手順:
1. `https://www.youtube.com/@{handle}/about` を開く
2. JS実行: `document.querySelector('#description-container #expand')?.click()`
3. 「メールアドレスの表示」ボタンがある場合:
   - ボタンをクリック → reCAPTCHA チェック → 「送信」
   - 表示されたメール → O列に書き込む
4. ボタンがない場合: スキップ

### Step 3: X（Twitter）ブラウザ操作でフォロワー数・DM有無を取得（V列・W列）

V列・W列が空でU列（X URL）がある行を対象。

1アカウントあたりの手順:
1. `{X プロフィール URL}` を開く
2. JSで一括取得（セレクタ: `a[href*="verified_followers"]`）:
   ```javascript
   (function() {
     const el = document.querySelector('a[href*="verified_followers"]');
     let followers = '';
     if (el) {
       const m = el.innerText.match(/([\d.,万千億]+)\s*フォロワー/);
       followers = m ? m[1] : '';
     }
     const dmBtn = document.querySelector('[data-testid="sendDMFromProfile"]');
     return { followers: followers, dmEnabled: !!dmBtn };
   })()
   ```
3. followers → V列、dmEnabled → W列（`TRUE`/`FALSE`）に書き込む
4. DMボタンは画面右側に「メッセージ」アイコンがあれば TRUE（目視でも確認可）

```python
svc.values().update(
    spreadsheetId="<SHEET_ID>",
    range="{シート名}!V{行番号}:W{行番号}",
    valueInputOption="RAW",
    body={"values": [["1.2万", "FALSE"]]},
).execute()
```

### Step 4: Facebook ブラウザ操作でフォロワー数・メール確認（Y列・O列補完）

Y列が空でX列（Facebook URL）がある行を対象。

**注意: Serper検索で取得したFacebook URLが別の同名ページの場合あり。必ず目視で確認すること。**  
- 同名ページの見分け方: フォロワー数が極端に少ない・所在地が違う・投稿内容が無関係
- 正しいURLが不明な場合は **サブエージェントで徹底調査**（下記参照）

#### Facebook URL が怪しい場合のサブエージェント調査

```
Agent(general-purpose):
  「{著者名} の公式FacebookページのURLを徹底的に調べてください。
  公式HP: {HP_URL}
  現在のURL {現在のURL} は別の同名ページの可能性あり。
  1. WebSearchで「{著者名} Facebook 公式」「site:facebook.com {著者名}」で検索
  2. WebFetchで公式HPのHTMLからFacebookリンクを探す（フッター・SNSアイコン等）
  3. 試験科別ページ（/gyosei/ /shihoshoshi/ 等）も確認
  見つかったURLと公式と判断した根拠を報告してください。」
```

判断基準（正しいページの特徴）:
- 所在地が本部と一致
- 公式HPドメインのメールアドレスが掲載されている
- 投稿内容が著者・組織の本業と一致
- フォロワー数が規模感に合っている

#### 公式ページと個人アカウントが両方ある場合

著者によっては公式ページ（企業・活動）と個人プロフィールの2つが存在する場合がある。

- **X列（Facebook URL）**: 公式ページ（フォロワー数が多い方・活動内容に即した方）を入れる
- **N列（備考）**: 個人アカウントURLを `Facebook個人アカウント: {URL}` の形式で記載する

```python
svc.values().update(spreadsheetId="<SHEET_ID>", range="{シート名}!X{行番号}",
    valueInputOption="RAW", body={"values": [["https://www.facebook.com/公式ページ/"]]}).execute()
svc.values().update(spreadsheetId="<SHEET_ID>", range="{シート名}!N{行番号}",
    valueInputOption="RAW", body={"values": [["Facebook個人アカウント: https://www.facebook.com/個人ページ/"]]}).execute()
```

1ページあたりの手順:
1. `{Facebook URL}` を開く（JSでフォロワー数取得）:
   ```javascript
   document.body.innerText.match(/([\d,万千億]+)\s*人がフォロー|([\d,万千億]+)\s*フォロワー/)
   ```
2. フォロワー数・所在地・メールを確認 → 怪しければサブエージェント調査
3. 「基本データ」タブ → メールアドレスが載っていればO列に書き込む
4. Y列にフォロワー数を書き込む

```python
svc.values().update(
    spreadsheetId="<SHEET_ID>",
    range="{シート名}!Y{行番号}",
    valueInputOption="RAW",
    body={"values": [["1477"]]},
).execute()
```

### Step 5: Instagram ブラウザ操作でフォロワー数を取得（AA列）

AA列が空でZ列（Instagram URL）がある行を対象。

1アカウントあたりの手順:
1. `{Instagram URL}` を開く
2. プロフィール上部に「フォロワー〇〇人」と表示される（例: `フォロワー1225人`）
3. AA列にフォロワー数（数字のみ）を書き込む

```python
svc.values().update(
    spreadsheetId="<SHEET_ID>",
    range="{シート名}!AA{行番号}",
    valueInputOption="RAW",
    body={"values": [["1225"]]},
).execute()
```

## 環境・前提条件

| 項目 | 内容 |
|------|------|
| 環境変数 | `SERPER_KEY`（~/.bash_profile に設定済み） |
| 認証ファイル | `credentials.json`（プロジェクトフォルダに配置） |
| シート共有 | `id-60525-sns-collection@sns-collection-497403.iam.gserviceaccount.com` に編集者権限 |
| ブラウザ操作 | Claude Code + Claude-in-Chrome MCP が必要（Step 2〜5） |

## コスト

- Serper.dev 無料枠 2,500件/月 → 約 800〜1,200 人分処理可能
- ブラウザ操作（YouTube/X/Facebook/Instagram）は無料（時間コストのみ）

## よくある間違いと対処法

### O列（メール）が空になる
**原因**: Step 1（main.py）ではYouTubeの「メールアドレスの表示」機能を使わないため、チャンネル概要欄のビジネスメールが取得できない。サブエージェントのWeb検索でも非公開のため発見不可。  
**対処**: **各行の入力後に必ずStep 2（youtube_email_batch.py）を実施する。** S列にYouTubeがある著者のO列が空なら必ず確認すること。参照シートとの比較で発見できるが、比較前に実施するのが正しい順序。

### O列（メール）がHPフッターに載っているのに取得できない
**原因**: `hp_scraper.py` のスクレイピングがフッター部分のメールアドレスを取得できない場合がある。contactページにフォームのみ存在し、メールはトップページフッターにのみ記載されているケースで発生。  
**対処**: 参照シートとの比較でO列が空←になっていたら、公式HPのトップページフッターを目視確認する。または以下でHPのテキストを直接確認する:
```python
# HPのフルテキストからメールを探す
import re, requests
html = requests.get('https://公式HP').text
emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', html)
print([e for e in emails if 'example' not in e])
```

### R列（ブログ）で外部ブログサービスを優先してしまう
**原因**: サブエージェントへの指示が「ブログURL」と曖昧な場合、AmebloやnoteなどをHP内ブログより優先して返すことがある。  
**対処**: サブエージェントへのプロンプトに「公式HP内のブログ（/blog等）がある場合はそちらを優先する」と明示する。また公式HPをWebFetchで確認する際にブログリンクも確認すること。

### S列（YouTube URL）がチャンネルIDベースになる
**原因**: Serperの検索結果が `youtube.com/channel/UC...` 形式のURLを返すことがある。  
**対処**: `@ハンドル名/featured` 形式に統一する（例: `https://www.youtube.com/@takahashi_yoichi/featured`）。チャンネルページを開いてアドレスバーのURLを使うのが確実。

### X列（Facebook）で法人ページと個人ページを混同する
**原因**: 著者によっては個人プロフィールと法人・活動ページの両方が存在する。Serper検索では法人ページがヒットしやすいが、本人への連絡先としては個人ページが有用な場合もある。  
**対処**:
- X列には**本人確認できるページ**（経歴・投稿内容・所在地が一致）を入れる
- フォロワー数が多い方・活動内容に即した方を優先
- もう一方はN列（備考）に `Facebook個人アカウント: {URL}` として記載
- 偽アカウントが多い著者（例: 高橋洋一）はN列に注意書きを入れる

### YouTube URLのハンドル確認方法
チャンネルIDベースURL（`/channel/UC...`）とハンドルURL（`/@xxx`）は同一チャンネル。  
チャンネルページ上部の `@ハンドル名` を確認して `/featured` を付けて統一する。

## 注意事項

- Q列（HP）に問い合わせページが入らないよう除外済み（`inquir` / `contact` / `/form` を含むURLはQに入らない）
- URLの `#アンカー` は自動除去される
- X列（Facebook）は非公式ページが収集される場合あり → 公式HPのリンクから正しいURLを確認して上書き
- Facebook公式ページにはメールアドレスが載っていることが多い → O列の補完に活用
- このツールは Claude Code 環境が必要なため他者への配布は不可
