"""ステージングJSONの内容を本番列(O〜AA)に昇格させる。
サブエージェント検証＋ブラウザでのフォロワー数取得が完了したら使う。

使い方:
    # 検証ログを書く（必須）
    echo "サブエージェント調査結果..." > verifications/ビジネス書_17.md

    # 値を上書き編集してから昇格
    python3 promote.py --sheet-id <ID> --sheet "ビジネス書" --row 17 --verified

オプション:
    --set O="email@example.com" --set T="2.89万" のように個別上書き可能
"""
import argparse
import json
import os
import sys

from sheets import _service

BASE = os.path.dirname(os.path.abspath(__file__))
STAGING_DIR = os.path.join(BASE, "staging")
VERIFY_DIR = os.path.join(BASE, "verifications")

COL_MAP = {
    "O": "email",
    "P": "contact_form_url",
    "Q": "company_hp",
    "R": "blog_url",
    "S": "youtube_url",
    "T": "youtube_subscribers",
    "U": "x_url",
    "V": "x_followers",
    "W": None,  # TwitterDM
    "X": "facebook_url",
    "Y": None,  # FBフォロワー
    "Z": "instagram_url",
    "AA": None,  # IGフォロワー
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet-id", required=True)
    ap.add_argument("--sheet", required=True, help="シート名（例: ビジネス書）")
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--verified", action="store_true",
                    help="サブエージェント検証完了を明示（必須）")
    ap.add_argument("--set", action="append", default=[],
                    help='列=値 形式の上書き（例: --set O="mail@x.com"）')
    ap.add_argument("--clear-n", action="store_true", default=True,
                    help="N列の⚠️未検証マーカーをクリア（既定: ON）")
    ap.add_argument("--n-note", default="",
                    help="N列に書く備考（指定なければクリアのみ）")
    args = ap.parse_args()

    if not args.verified:
        print("❌ --verified フラグが必須です。サブエージェント検証完了を明示してください。")
        sys.exit(1)

    safe_sheet = args.sheet.replace("/", "_")
    staging_path = os.path.join(STAGING_DIR, f"{safe_sheet}_{args.row}.json")
    verify_path = os.path.join(VERIFY_DIR, f"{safe_sheet}_{args.row}.md")

    if not os.path.exists(staging_path):
        print(f"❌ ステージングが存在しません: {staging_path}")
        print("   先に `python3 main.py --row {args.row} --overwrite` を実行してください。")
        sys.exit(1)

    if not os.path.exists(verify_path):
        print(f"❌ 検証ログが存在しません: {verify_path}")
        print("   サブエージェント調査結果を以下に保存してから再実行してください:")
        print(f"   {verify_path}")
        sys.exit(1)

    with open(staging_path, encoding="utf-8") as f:
        data = json.load(f)
    record = data["record"]

    # --set 上書き
    overrides = {}
    for kv in args.set:
        if "=" not in kv:
            print(f"❌ --set の形式が不正: {kv}")
            sys.exit(1)
        col, val = kv.split("=", 1)
        col = col.strip().upper()
        overrides[col] = val

    # O〜AA の値配列を構築
    cols_order = ["O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "AA"]
    values = []
    for col in cols_order:
        if col in overrides:
            values.append(overrides[col])
        elif COL_MAP[col] is None:
            values.append("")
        else:
            values.append(record.get(COL_MAP[col], "") or "")

    svc = _service()
    svc.values().update(
        spreadsheetId=args.sheet_id,
        range=f"{args.sheet}!O{args.row}:AA{args.row}",
        valueInputOption="RAW",
        body={"values": [values]},
    ).execute()

    # N列の処理
    n_value = args.n_note if args.n_note else ""
    svc.values().update(
        spreadsheetId=args.sheet_id,
        range=f"{args.sheet}!N{args.row}",
        valueInputOption="RAW",
        body={"values": [[n_value]]},
    ).execute()

    # ステージング側に verified フラグを保存
    data["verified"] = True
    with open(staging_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 昇格完了: {args.sheet} 行{args.row}")
    print(f"   O〜AA を本番列に書き込み / N列マーカーをクリア")


if __name__ == "__main__":
    main()
