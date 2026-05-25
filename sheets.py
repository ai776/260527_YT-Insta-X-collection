"""Google Sheets の読み書き"""
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from models import PersonRecord

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _service():
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds).spreadsheets()


def read_input(spreadsheet_id: str, range_: str = "入力!A2:B") -> list[PersonRecord]:
    """入力シートから名前・会社を読み込む（A列: 名前, B列: 会社）"""
    svc = _service()
    result = svc.values().get(spreadsheetId=spreadsheet_id, range=range_).execute()
    rows = result.get("values", [])
    records = []
    for row in rows:
        name = row[0].strip() if row else ""
        company = row[1].strip() if len(row) > 1 else ""
        if name:
            records.append(PersonRecord(name=name, company=company))
    return records


def write_output(spreadsheet_id: str, records: list[PersonRecord], sheet_name: str = "出力"):
    """出力シートに結果を書き込む（既存データを上書き）"""
    svc = _service()

    # シートを確認・作成
    meta = svc.get(spreadsheetId=spreadsheet_id).execute()
    existing = [s["properties"]["title"] for s in meta["sheets"]]
    if sheet_name not in existing:
        svc.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
        ).execute()

    rows = [PersonRecord.headers()] + [r.to_row() for r in records]
    svc.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()
    print(f"[Sheets] {len(records)} 件を '{sheet_name}' に書き込みました")


def append_output(spreadsheet_id: str, record: PersonRecord, sheet_name: str = "出力"):
    """1件ずつ追記（処理中に中断しても途中まで保存される）"""
    svc = _service()
    svc.values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [record.to_row()]},
    ).execute()
