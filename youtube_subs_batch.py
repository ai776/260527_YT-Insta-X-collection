"""
YouTubeチャンネルの登録者数をブラウザ操作で取得してT列に書き込む。
Claude-in-Chrome MCP が使えるセッション内で実行すること。

使い方:
    python3 youtube_subs_batch.py --sheet-id <ID> [--limit 10]

処理フロー:
1. S列（YouTube URL）があり T列（登録者数）が空の行を対象
2. ブラウザでチャンネルページを開く
3. ページテキストから「チャンネル登録者数 X.X万」を取得
4. T列に書き込む
"""
import argparse
import re
from sheets import _service

SHEET_NAMES = ["ビジネス書", "スピリチュアル・自己啓発", "教養・雑学", "生活・実用書"]
SUB_RE = re.compile(r"チャンネル登録者数\s*([\d.,]+\s*[万千億]?(?:\s*人)?)")


def read_targets(spreadsheet_id: str, overwrite: bool = False) -> list[dict]:
    """S列にYouTube URL があり T列が空（またはoverwrite）の行を収集"""
    svc = _service()
    targets = []
    for sheet in SHEET_NAMES:
        result = svc.values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet}!A1:AA",
        ).execute()
        rows = result.get("values", [])
        for i, row in enumerate(rows[1:], start=2):
            yt_url = row[18].strip() if len(row) > 18 else ""   # S列
            subs = row[19].strip() if len(row) > 19 else ""     # T列
            name = row[8].strip() if len(row) > 8 else ""       # I列
            if yt_url and name and (not subs or overwrite):
                targets.append({
                    "sheet": sheet,
                    "row_num": i,
                    "name": name,
                    "yt_url": yt_url,
                })
    return targets


def to_channel_url(yt_url: str) -> str:
    """YouTube URL をチャンネルのトップページURLに変換。非チャンネルURLは空文字"""
    url = yt_url.split("?")[0].rstrip("/")
    if not url.startswith("http"):
        return ""
    if any(x in url for x in ["/watch", "playlist", "/shorts/", "/videos/", "hashtag"]):
        return ""
    # /about を除去してトップページに統一
    url = url.replace("/about", "")
    return url


def write_subs(spreadsheet_id: str, sheet: str, row_num: int, subs: str):
    svc = _service()
    svc.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet}!T{row_num}",
        valueInputOption="RAW",
        body={"values": [[subs]]},
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
        ch_url = to_channel_url(t["yt_url"])
        if not ch_url:
            print(f"[{i}] {t['name']}: チャンネルURLでないのでスキップ ({t['yt_url']})")
            continue
        print(f"[{i}/{len(targets)}] {t['sheet']} 行{t['row_num']}: {t['name']} → {ch_url}")


if __name__ == "__main__":
    main()
