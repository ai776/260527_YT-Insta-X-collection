"""
営業リスト自動収集ツール
既存スプレッドシートのI列（著者名）・J列（URL）を読み、O〜AA列に書き込む

使い方:
    python3 main.py --sheet-id <ID> [--limit 10] [--overwrite]
"""
import argparse
import json
import os
import sys
import time
from dataclasses import asdict

from sheets import _service
from searcher import search_sns, search_hp, search_blog, search_email
from scrapers.hp_scraper import scrape_hp
from scrapers.youtube_browser import to_about_url
from models import PersonRecord

SHEET_ID = None  # 引数で渡す
SHEET_NAME = "シート1"  # 実際のシート名
STAGING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "staging")

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
    """ステージングJSONに記録し、N列に未検証マーカーのみシート書き込み。
    本番列(O〜AA)への書き込みは promote.py 経由でのみ実行される。"""
    # N列に未検証マーカーを付与（サブエージェント検証完了後 promote.py でクリア）
    svc = _service()
    svc.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{SHEET_NAME}!N{row_num}",
        valueInputOption="RAW",
        body={"values": [["⚠️未検証（サブエージェントで本人特定後に promote.py で昇格）"]]},
    ).execute()
    # ステージングJSONに保存（本番列には書かない）
    os.makedirs(STAGING_DIR, exist_ok=True)
    safe_sheet = SHEET_NAME.replace("/", "_")
    path = os.path.join(STAGING_DIR, f"{safe_sheet}_{row_num}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "sheet_name": SHEET_NAME,
            "row_num": row_num,
            "name": record.name,
            "record": asdict(record),
            "verified": False,
        }, f, ensure_ascii=False, indent=2)


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
            print(f"  ⚠️ 未検証: この行はサブエージェントで本人特定が必要です（行{row['row_num']}）")
        except Exception as e:
            print(f"  エラー: {e}")
        time.sleep(0.5)

    print(f"\n完了: {len(all_targets)} 件処理しました")
    print("=" * 60)
    print("⚠️ 必須次工程: 各行についてサブエージェント(general-purpose)で")
    print("   本人特定 + URL検証を行ってからシートを確定すること。")
    print("   省略すると同名別人・別組織への誤マッチが残ります。")
    print("   詳細は .claude/skills/sales-list-collect/SKILL.md を参照。")
    print("=" * 60)


if __name__ == "__main__":
    main()
