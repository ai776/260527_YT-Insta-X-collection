"""
YouTubeチャンネルの「メールアドレスを表示」ボタンをブラウザ操作で取得する。
Claude-in-Chrome MCP が使えるセッション内で実行すること。

使い方（Claude Code から）:
    /run python3 youtube_email_batch.py --sheet-id <ID> [--limit 10]

処理フロー:
1. シートのS列（YouTube URL）がある行を取得
2. O列（メール）が空の行だけ対象
3. ブラウザでチャンネルの概要モーダルを開く
4. 「メールアドレスを表示」ボタンがあればクリック → O列に書き込む
5. ボタンがなければスキップ
"""
import argparse
import time
import re
from sheets import _service

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
FAKE = (".png", ".jpg", ".gif", ".woff", ".svg", "example.com", "sentry.io")
SHEET_NAMES = ["ビジネス書", "スピリチュアル・自己啓発", "教養・雑学", "生活・実用書"]


def read_targets(spreadsheet_id: str) -> list[dict]:
    """S列にYouTube URL があり O列が空の行を収集"""
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
            email = row[14].strip() if len(row) > 14 else ""    # O列
            name = row[8].strip() if len(row) > 8 else ""       # I列
            if yt_url and not email and name:
                targets.append({
                    "sheet": sheet,
                    "row_num": i,
                    "name": name,
                    "yt_url": yt_url,
                })
    return targets


def to_about_url(yt_url: str) -> str:
    """YouTube URL を /about URL に変換"""
    url = yt_url.split("?")[0].rstrip("/")
    # watch?v= や playlist? は チャンネルURLでないのでスキップ
    if "/watch" in url or "playlist" in url or "/shorts/" in url:
        return ""
    if "/about" not in url:
        url += "/about"
    return url


def write_email(spreadsheet_id: str, sheet: str, row_num: int, email: str):
    svc = _service()
    svc.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet}!O{row_num}",
        valueInputOption="RAW",
        body={"values": [[email]]},
    ).execute()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-id", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    print("対象行を読み込み中...")
    targets = read_targets(args.sheet_id)
    if args.limit > 0:
        targets = targets[:args.limit]
    print(f"{len(targets)} 件を処理します\n")
    print("=" * 50)
    print("このスクリプトはブラウザ操作の手順を出力します。")
    print("Claude Code のブラウザ自動化機能と組み合わせて使用してください。")
    print("=" * 50)

    for i, t in enumerate(targets, 1):
        about_url = to_about_url(t["yt_url"])
        if not about_url:
            print(f"[{i}] {t['name']}: YouTubeチャンネルURLでないのでスキップ ({t['yt_url']})")
            continue
        print(f"\n[{i}/{len(targets)}] {t['name']} ({t['sheet']} 行{t['row_num']})")
        print(f"  URL: {about_url}")
        print(f"  → ブラウザで開き、概要モーダルの「メールアドレスを表示」を確認")


if __name__ == "__main__":
    main()
