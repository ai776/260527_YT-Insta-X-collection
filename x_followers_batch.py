"""
X(Twitter)のフォロワー数をブラウザ操作で取得してV列に書き込む。
Claude-in-Chrome MCP が使えるセッション内で実行すること。

使い方:
    python3 x_followers_batch.py --sheet-id <ID> [--limit 10]

処理フロー:
1. U列（X URL）があり V列（フォロワー数）が空の行を対象
2. ブラウザでXプロフィールページを開く
3. JS でフォロワー数を取得
4. V列に書き込む
"""
import argparse
import re
from sheets import _service

SHEET_NAMES = ["ビジネス書", "スピリチュアル・自己啓発", "教養・雑学", "生活・実用書"]


def read_targets(spreadsheet_id: str, overwrite: bool = False) -> list[dict]:
    """U列にX URL があり V列が空（またはoverwrite）の行を収集"""
    svc = _service()
    targets = []
    for sheet in SHEET_NAMES:
        result = svc.values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet}!A1:AA",
        ).execute()
        rows = result.get("values", [])
        for i, row in enumerate(rows[1:], start=2):
            x_url = row[20].strip() if len(row) > 20 else ""    # U列
            followers = row[21].strip() if len(row) > 21 else "" # V列
            name = row[8].strip() if len(row) > 8 else ""        # I列
            if x_url and x_url.startswith("http") and name and (not followers or overwrite):
                targets.append({
                    "sheet": sheet,
                    "row_num": i,
                    "name": name,
                    "x_url": x_url,
                })
    return targets


def write_followers(spreadsheet_id: str, sheet: str, row_num: int, followers: str):
    svc = _service()
    svc.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet}!V{row_num}",
        valueInputOption="RAW",
        body={"values": [[followers]]},
    ).execute()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-id", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    print("対象行を読み込み中...")
    targets = read_targets(args.sheet_id, overwrite=args.overwrite)
    if args.limit > 0:
        targets = targets[:args.limit]
    print(f"{len(targets)} 件を処理します\n")

    for i, t in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {t['sheet']} 行{t['row_num']}: {t['name']} → {t['x_url']}")


if __name__ == "__main__":
    main()
