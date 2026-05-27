---
name: sales-list-collect
description: >
  著者名リストが入ったGoogleスプレッドシートを受け取り、
  SNS・メール・問い合わせフォーム・HP・ブログを収集してO〜AA列に書き込む。
  サブエージェント(general-purpose)による本人特定＋ブラウザ操作で取得する方式。
  ※Serper.dev は誤マッチ多発のため2026-05時点で廃止。
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
| O  | メールアドレス | **サブエージェント調査** / HPスクレイピング / Facebook / YouTube |
| P  | 問い合わせページURL | **サブエージェント調査** / HPスクレイピング |
| Q  | 会社HP・公式サイト | **サブエージェント調査**（WebSearch+WebFetch） |
| R  | ブログ（ameba/note/はてな等） | **サブエージェント調査** |
| S  | YouTube チャンネル | **サブエージェント調査**（or 既知URL） |
| T  | YouTube 登録者数 | ブラウザ操作（`youtube_subs_batch.py`） |
| U  | Twitter/X | **サブエージェント調査**（or 既知URL） |
| V  | Twitterフォロワー数 | ブラウザ操作（`x_followers_batch.py`） |
| W  | TwitterDM有無 | ブラウザ操作（XプロフィールJS） |
| X  | Facebook | **サブエージェント調査**（目視確認推奨） |
| Y  | Facebookフォロワー数 | ブラウザ操作（Facebookページ） |
| Z  | Instagram | **サブエージェント調査**（or 既知URL） |
| AA | Instagramフォロワー数 | ブラウザ操作（Instagramページ） |

> ⚠️ **Serper.dev は本スキルから廃止しました（2026-05）。**  
> インフルエンサーの本名と異なるSNS表示名（芸名・キャッチコピー）では同名別人の誤マッチが頻発するため、Serperでの自動収集は中止。代わりに `general-purpose` サブエージェントが WebSearch + WebFetch で本人特定→公式情報を取得する方式に統一。  
> 旧 `searcher.py` `main.py` は残存しているが新規実行では使わない。

## ワークフロー

### 処理順の原則: 3SNS → 2SNS → 1SNS

人物統合シートで「SNS数」列の降順に処理する。営業効果が高い層から潰す。

| 優先度 | 対象 | 理由 |
|---|---|---|
| 1 | SNS数=3 | 全SNSで活動中＝最有力ターゲット |
| 2 | SNS数=2 | 活動規模ある層 |
| 3 | SNS数=1 | 数が多く効率悪い。フォロワー数で更にフィルタ推奨 |

> 1SNSのみ層が大半（数千件）になるので、フォロワー数閾値（例: 1万以上）で更に絞ってから着手するのが現実的。

### Step 1: SNS・HP・メール・ブログ収集（サブエージェント方式）

各人物につき `general-purpose` サブエージェントを1体起動し、WebSearch + WebFetch で本人特定→公式情報を取得する。複数人を**並列実行**できる（5〜10体推奨）。

#### サブエージェントへの依頼テンプレート

```
「{氏名}」というインフルエンサー/著者の本人特定と連絡先を調査してください。

## 既知情報
- YouTube: {URL}（チャンネル名「{表示名}」、登録{N}万）
- Instagram: {URL}（フォロワー{N}万）
- X: {URL}（フォロワー{N}万）
- ハンドル: {handle}

## 調査依頼
WebSearch/WebFetchで以下を特定:
1. 所属事務所/会社HP・公式サイト
2. メールアドレス（仕事依頼用）
3. 問い合わせフォームURL
4. ブログ（ameba/note等含む）
5. Facebook

## 重要
- 同名別人に注意。SNSハンドル `{handle}` と一致する人物のみ採用
- URLは実在性をWebFetchで確認
- 確証取れないものは「未確認」と明記

## 出力形式
```json
{"company_hp":"","email":"","contact_form_url":"","blog_url":"",
 "facebook_url":"","confidence":"high|medium|low","evidence":"根拠2-3行"}
```
```

#### 結果の保存

1. 検証ログを **必ず** `verifications/{シート名}_{データ行番号}_{ハンドル}.md` に保存（行番号はデータ行=1始まり、シート行ではない）
2. confidence と evidence を残す
3. シートのN列(備考)に `所属:X / ※サブエージェント検証済(信頼度)` を記載

#### セルの記載ルール（厳守）

未取得項目を1表記で済ませず、状態に応じて使い分ける:

| 表記 | 意味 |
|---|---|
| URL/メール記載 | 確認済み |
| **未確認** | 調査したが見つからなかった（実在する可能性は残る） |
| **該当なし** | 公式運用なしが濃厚（事務所所属で公式FB持たない、本人がbioで「やってません」と明記等、状況証拠が揃う場合） |
| 空セル | 未調査 |

サブエージェントの evidence が「確認できず」「未公開」等の場合は **未確認** を使用。
「公式運用なし」「掲載なし」と明確に断言できる場合のみ **該当なし** を使う。

#### Step 1.5: SNSリンク相互検証（推奨）

サブエージェントが特定したHP/Blog/問い合わせURLが本物かを、**そのページに記載されているSNSリンクが既知URLと一致するか**で二重チェックする。

##### サブエージェントへの依頼テンプレート

```
HPに記載されているSNSリンクが既知のSNSアカウントと一致するか検証してください。

## 対象人物: {氏名}
## 検証先URL
- HP: {HP_URL}
- Blog: {Blog_URL}（あれば）

## 既知の本人SNS
- YouTube: {YT_URL}
- Instagram: {IG_URL}
- X: {X_URL}

## 手順
1. WebFetchで各URLを開く
2. ページ内のSNSリンク（YT/IG/X/FB等）を全て抽出
3. 既知URLと一致するか比較

## 出力
{"hp_status":"reachable|unreachable","sns_found":{...},
 "match":{"youtube":"match|mismatch|not_found",...},
 "verdict":"confirmed_self|suspicious|inconclusive","note":"..."}
```

##### 判定の扱い

| verdict | 行の背景色 | RGB | 扱い |
|---|---|---|---|
| `confirmed_self` | 🟢 緑 | (0.85, 0.95, 0.85) | N列備考に `※SNSリンク相互一致✓` を追記 |
| `inconclusive` | 🟡 黄 | (1.0, 0.9, 0.6) | HPがリンクハブ系/事務所経由でSNS記載なし。N列に `※SNSクロス検証不可(理由)` を追記 |
| `suspicious` | 🔴 赤 | (1.0, 0.8, 0.8) | **誤マッチ疑い**。HPを空に戻し、サブエージェント再調査 |

##### 色付けコード例

```python
from sheets import _service
svc=_service()
SID='<SHEET_ID>'
sid=<sheetId>  # 対象シートのID
# 行N (1-indexed) を緑にする例
svc.batchUpdate(spreadsheetId=SID, body={'requests':[{
  'repeatCell':{
    'range':{'sheetId':sid,'startRowIndex':N-1,'endRowIndex':N,
              'startColumnIndex':0,'endColumnIndex':18},
    'cell':{'userEnteredFormat':{'backgroundColor':{'red':0.85,'green':0.95,'blue':0.85}}},
    'fields':'userEnteredFormat.backgroundColor'
  }}]}).execute()
```

##### 注意
- HP上のYouTubeリンクは `youtube.com/channel/UC...` 形式のことがある。チャンネル名で本人確認すれば match 扱いでOK
- TikTok/楽天ROOM等の追加SNSがbioに載っていれば、ハンドル一致を本人確証の補強として使える

#### 取得率の実測（2026-05時点）

サブエージェント方式で得られた結果（パイロット4人）:
- 3人がhigh信頼度で本人特定成功
- 1人がmedium（公式HPなし、SNS完結タイプ）
- Serper方式と比較して**誤マッチほぼゼロ・取得率大幅向上**

> ⚠️ **Step 1完了後は必ずStep 2/2.5/3/4/5を実行すること。**  
> 各SNSのフォロワー数・YT概要のメールはブラウザ操作でしか取れない。  
> Step 2.5（youtube_email_batch.py）をスキップするとO列が永久に空のままになる。

### 共通: 休眠アカウント検出（Step 2〜5に組み込む）

各SNSのフォロワー数取得時、**最終投稿日も同時に取得**してN列備考に追記する。半年以上更新なしのアカウントは営業効率が悪いため除外対象とする。

| SNS | 最終投稿日の取得方法 |
|---|---|
| YouTube | チャンネル動画タブ最新動画の投稿日（`yt-formatted-string#metadata-line` 等） |
| Instagram | プロフィール最新投稿の日付（投稿開いて確認） |
| X | プロフィール最新ツイートのタイムスタンプ |
| Facebook | 最新投稿の日付 |

備考に `※YT最終投稿2024-11 / IG最終2025-08` のように記載。  
**最終投稿が現在から6ヶ月超のアカウントは行を黄色(休眠候補)**にマークすると視覚的に分かる。

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
| 環境変数 | （Serper廃止により不要） |
| 認証ファイル | `credentials.json`（プロジェクトフォルダに配置） |
| シート共有 | `id-60525-sns-collection@sns-collection-497403.iam.gserviceaccount.com` に編集者権限 |
| ブラウザ操作 | Claude Code + Claude-in-Chrome MCP が必要（Step 2〜5） |

## コスト

- サブエージェント方式: 1人あたり ~30秒・並列5〜10体で時短可能
- ブラウザ操作（YouTube/X/Facebook/Instagram）は無料（時間コストのみ）

## ⚠️ 最重要ワークフロー（厳守）

**各行を処理する際、必ず以下の順序で実行すること:**

1. **サブエージェント（general-purpose）で本人特定 & 連絡先調査**（Step 1のテンプレート使用）
2. 検証ログを `verifications/` に保存（confidence + evidence を残す）
3. ブラウザ（Claude-in-Chrome）で各SNSのフォロワー数を取得（Step 2〜5）
4. シートに書き込み（O〜AA列 + N列備考）
5. 参照シート（1US8ucThOaxWvI9oxnmA0yXx0lmYxT4VYdGS2AW7tKys）と比較

**なぜサブエージェント調査が抜けるのか（根本原因）**:

1. **確証バイアス**: main.pyは必ずURL形式の文字列を返すため「それらしい」値を見ると形式の正しさで本人と錯覚する。中身が別人でも気付かない。
2. **例外処理として誤分類**: 「よくある間違い」セクションに記載していたため「怪しい時だけ使う救済策」と心理的に位置付け、デフォルト工程から外していた。
3. **コスト最適化の暴走**: サブエージェントはトークン/時間コストが高いため「不要そうなら省略」が無意識に発動。ユーザーの「徹底」要求より省力化を優先してしまう。
4. **行ごとに文脈リセット**: ループ処理で前行の失敗教訓を忘却し「次の行は単純そう」と毎回再判断するためぶれる。
5. **同名別人問題の頻度過小評価**: X3/U6/X10/コンプライアンス研究会など繰り返し失敗しているのに「今回は大丈夫そう」と希望的観測で再発させる。
6. **受動性**: ユーザーが「怪しい」と指摘するまで動かない。本来は無条件で疑うべき。

**対策（強制ゲート）**:
- main.py 実行直後は**シートに書き込む前に**サブエージェントを呼ぶ。書き込み前にこの工程を踏まないと進めない、という順序を厳守する。
- 「出力が整っている」「公式っぽい」「ドメインが合っている」は本人特定の根拠にしない。Amazon等で著作→著者プロフィール→公式という**逆引き経路**でのみ確定する。
- 過去事例（X3, U6, X10, コンプライアンス研究会等）を見て「自分は必ず間違える前提」で動く。

**サブエージェントを後回しにしない理由**:
- 自動収集の結果が"正しそうに見える"場合でも、同名別人・別組織・別ドメインの誤マッチが頻発する（例: コンプライアンス研究会→湊法律事務所、X3→伊藤塾と別の小学校学習塾、U6→@takaramap別人、X10→@akinori_0226別人）
- 違和感が出てから調査するのは二度手間。最初から徹底調査することで一発で確定する
- 「公式と思われる」「正しそう」という主観判断はせず、必ずサブエージェント経由で出版書籍の版元・著者プロフィールから逆引きで特定する

**サブエージェントへの指示テンプレート**:
```
著者「{著者名}」（{ジャンル}の著者）について、本人を特定し以下を返してください。
背景: 自動収集で以下が取れたが本人かどうか要検証
- X: {自動収集値}
- YT: {自動収集値}
- Mail: {自動収集値}
- Form: {自動収集値}

調査タスク:
1. Amazon等で著作を検索し、本人プロフィール・所属を特定
2. 公式HPを特定し WebFetch で確認
3. 以下の列を埋めるURLを返す:
   - O: メール / P: 問い合わせ / Q: HP / R: ブログ
   - S: YouTube（@handle/featured 形式）/ U: X / X: Facebook / Z: Instagram
4. 各URLが本人公式であることを WebSearch/WebFetch で確認
特定不可なら明記。300語以内。
```

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
