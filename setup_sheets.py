"""
スプレッドシートの初期セットアップ（入力シートにサンプルデータ・ヘッダーを作成）

使い方:
    python setup_sheets.py --sheet-id <スプレッドシートID>
"""
import argparse
from sheets import _service
from models import PersonRecord


def setup(sheet_id: str):
    svc = _service()

    # 入力シートを確認・作成
    meta = svc.get(spreadsheetId=sheet_id).execute()
    existing = [s["properties"]["title"] for s in meta["sheets"]]

    for sheet_name in ["入力", "出力"]:
        if sheet_name not in existing:
            svc.batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
            ).execute()
            print(f"シート '{sheet_name}' を作成しました")

    # 入力シートにヘッダー + サンプル
    sample_data = [
        ["名前", "会社・組織（任意）"],
        ["山本智也", "スカイ"],
        ["堀江貴文", ""],
        ["前田裕二", "UUUM"],
    ]
    svc.values().update(
        spreadsheetId=sheet_id,
        range="入力!A1",
        valueInputOption="RAW",
        body={"values": sample_data},
    ).execute()

    # 出力シートにヘッダー
    svc.values().update(
        spreadsheetId=sheet_id,
        range="出力!A1",
        valueInputOption="RAW",
        body={"values": [PersonRecord.headers()]},
    ).execute()

    print(f"セットアップ完了: https://docs.google.com/spreadsheets/d/{sheet_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-id", required=True)
    args = parser.parse_args()
    setup(args.sheet_id)
