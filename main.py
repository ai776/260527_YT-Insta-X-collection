"""
営業リスト自動収集ツール
既存スプレッドシートのI列（著者名）・J列（URL）を読み、O〜AA列に書き込む

使い方:
    python3 main.py --sheet-id <ID> [--limit 10] [--overwrite]
"""
import argparse
import os
import sys
import time

from sheets import _service
from searcher import search_sns, search_hp, search_blog, search_email
from scrapers.hp_scraper import scrape_hp
from scrapers.youtube_browser import to_about_url
from models import PersonRecord

SHEET_ID = None  # 引数で渡す
SHEET_NAME = "シート1"  # 実際のシート名

# O列=15番目(index 14) 〜 AA列=27番目(index 26)
# O:メール P:問い合わせ Q:HP R:ブログ S:YouTube T:YT登録者 U:Twitter
# V:TWフォロワー W:TWDM有無 X:Facebook Y:FBフォロワー Z:Instagram AA:IGフォロワー
COL_O = 14  # 0-indexed


def col_letter(index: int) -> str:
    """0-indexed の列番号をアルファベットに変換"""
    if index < 26:
        return chr(65 + index)
    return "A" + chr(65 + index - 26)


def read_rows(spreadsheet_id: str) -> list[dict]:
    svc = _service()
    result = svc.values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_NAME}!A1:AA",
    ).execute()
    rows = result.get("values", [])
    records = []
    for i, row in enumerate(rows[1:], start=2):  # 2行目から（1行目はヘッダー）
        name = row[8].strip() if len(row) > 8 else ""  # I列
        url = row[9].strip() if len(row) > 9 else ""   # J列
        if not name:
            continue
        # O列以降がすでに埋まっているかチェック
        filled = len(row) > COL_O and any(row[COL_O:])
        records.append({
            "row_num": i,
            "name": name,
            "url": url,
            "filled": filled,
            "existing": row,
        })
    return records


def write_row(spreadsheet_id: str, row_num: int, record: PersonRecord):
    """O〜AA列を1行分書き込む"""
    svc = _service()
    values = [
        record.email,            # O: メールアドレス
        record.contact_form_url, # P: 問い合わせページ
        record.company_hp,       # Q: HP
        record.blog_url,         # R: ブログ
        record.youtube_url,          # S: YouTube
        record.youtube_subscribers,  # T: YouTube登録者数
        record.x_url,            # U: Twitter
        record.x_followers,      # V: Twitterフォロワー数
        "",                      # W: TwitterDM有無
        record.facebook_url,     # X: Facebook
        "",                      # Y: Facebookフォロワー数
        record.instagram_url,    # Z: Instagram
        "",                      # AA: Instagramフォロワー数
    ]
    range_ = f"{SHEET_NAME}!O{row_num}:AA{row_num}"
    svc.values().update(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="RAW",
        body={"values": [values]},
    ).execute()


def process(name: str, company: str = "") -> PersonRecord:
    record = PersonRecord(name=name, company=company)
    record = search_sns(record)
    if not record.company_hp:
        record = search_hp(record)
    record = scrape_hp(record)
    record = search_blog(record)
    if not record.email:
        record = search_email(record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-id", required=True)
    parser.add_argument("--sheet-name", default="シート1", help="シート名")
    parser.add_argument("--limit", type=int, default=0, help="処理件数上限（0=全件）")
    parser.add_argument("--row", type=int, default=0, help="特定の行番号だけ処理（シート上の行番号）")
    parser.add_argument("--overwrite", action="store_true", help="既存データも上書き")
    args = parser.parse_args()

    # 処理対象シート（入力・出力シートは除外）
    svc = _service()
    meta = svc.get(spreadsheetId=args.sheet_id).execute()
    skip_sheets = {"入力", "出力"}
    target_sheets = [
        s["properties"]["title"]
        for s in meta["sheets"]
        if s["properties"]["title"] not in skip_sheets
    ]

    if args.sheet_name != "シート1":
        target_sheets = [args.sheet_name]

    all_targets = []
    for sheet_name in target_sheets:
        global SHEET_NAME
        SHEET_NAME = sheet_name
        rows = read_rows(args.sheet_id)
        unfilled = [r for r in rows if not r["filled"] or args.overwrite]
        print(f"  {sheet_name}: {len(unfilled)} 件未入力")
        for r in unfilled:
            r["sheet_name"] = sheet_name
        all_targets.extend(unfilled)

    if args.row > 0:
        all_targets = [r for r in all_targets if r["row_num"] == args.row]
    elif args.limit > 0:
        all_targets = all_targets[:args.limit]

    print(f"\n合計 {len(all_targets)} 件を処理します\n")

    for i, row in enumerate(all_targets, 1):
        SHEET_NAME = row["sheet_name"]
        name = row["name"]
        print(f"[{i}/{len(all_targets)}] [{SHEET_NAME}] {name}")
        try:
            record = process(name)
            write_row(args.sheet_id, row["row_num"], record)
            print(f"  X={record.x_url or '-'}, YT={record.youtube_url or '-'}, "
                  f"Mail={record.email or '-'}, Form={record.contact_form_url or '-'}")
        except Exception as e:
            print(f"  エラー: {e}")
        time.sleep(0.5)

    print(f"\n完了: {len(all_targets)} 件処理しました")


if __name__ == "__main__":
    main()
