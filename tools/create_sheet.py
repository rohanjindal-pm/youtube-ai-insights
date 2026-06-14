"""
Creates a Google Sheet with all YouTube AI insights data.

Input:  .tmp/insights.json
Output: Google Sheet URL (printed + saved to .tmp/sheet_url.txt)
"""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")
INSIGHTS_PATH = Path(".tmp/insights.json")


def get_creds():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def fmt_num(n) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def col(letter: str, row: int) -> str:
    return f"{letter}{row}"


def create_sheet(service, title: str) -> str:
    spreadsheet = {
        "properties": {"title": title},
        "sheets": [
            {"properties": {"title": "Summary"}},
            {"properties": {"title": "Top Videos (Views)"}},
            {"properties": {"title": "Top Videos (Engagement)"}},
            {"properties": {"title": "Top Channels"}},
            {"properties": {"title": "Rising Stars"}},
            {"properties": {"title": "Keywords"}},
            {"properties": {"title": "Upload Timing"}},
        ],
    }
    result = service.spreadsheets().create(body=spreadsheet).execute()
    return result["spreadsheetId"]


def batch_update(sheets_svc, sheet_id: str, data: list[dict]):
    sheets_svc.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "RAW", "data": data},
    ).execute()


def format_header_row(sheets_svc, sheet_id: str, sheet_name: str, num_cols: int):
    sheet_meta = sheets_svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sid = next(s["properties"]["sheetId"] for s in sheet_meta["sheets"]
               if s["properties"]["title"] == sheet_name)

    requests = [
        {
            "repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                           "startColumnIndex": 0, "endColumnIndex": num_cols},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.059, "green": 0.204, "blue": 0.376},
                        "textFormat": {"bold": True, "fontSize": 11,
                                       "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
    ]
    sheets_svc.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id, body={"requests": requests}
    ).execute()


def populate_summary(sheets_svc, sheet_id: str, insights: dict):
    s = insights["summary"]
    rows = [
        ["AI YouTube Insights Report"],
        ["Generated", insights.get("generated_at", "")[:10]],
        [],
        ["Metric", "Value"],
        ["Videos Analyzed", s["total_videos_analyzed"]],
        ["Total Views Tracked", s["total_views_across_all"]],
        ["Avg Engagement Rate (%)", s["avg_engagement_rate"]],
        ["Top Creator", s["top_creator"]],
        ["Top Video Title", s["top_video_title"]],
        ["Top Video Views", s["top_video_views"]],
    ]
    batch_update(sheets_svc, sheet_id, [{"range": "Summary!A1", "values": rows}])


def populate_top_videos_views(sheets_svc, sheet_id: str, insights: dict):
    headers = ["Title", "Channel", "Views", "Likes", "Comments", "Engagement %",
               "Published", "Days Old", "URL"]
    rows = [headers]
    for v in insights.get("top_by_views", []):
        rows.append([
            v["title"], v["channel"], v["views"], v["likes"], v["comments"],
            v.get("engagement_rate") or "",
            (v.get("publish_date") or "")[:10], v.get("days_old") or "",
            v["url"],
        ])
    batch_update(sheets_svc, sheet_id,
                 [{"range": "Top Videos (Views)!A1", "values": rows}])
    format_header_row(sheets_svc, sheet_id, "Top Videos (Views)", len(headers))


def populate_top_videos_engagement(sheets_svc, sheet_id: str, insights: dict):
    headers = ["Title", "Channel", "Engagement %", "Views", "Likes", "Comments",
               "Published", "URL"]
    rows = [headers]
    for v in insights.get("top_by_engagement", []):
        rows.append([
            v["title"], v["channel"], v.get("engagement_rate") or "",
            v["views"], v["likes"], v["comments"],
            (v.get("publish_date") or "")[:10], v["url"],
        ])
    batch_update(sheets_svc, sheet_id,
                 [{"range": "Top Videos (Engagement)!A1", "values": rows}])
    format_header_row(sheets_svc, sheet_id, "Top Videos (Engagement)", len(headers))


def populate_top_channels(sheets_svc, sheet_id: str, insights: dict):
    headers = ["Channel", "Avg Engagement %", "Avg Views", "Total Views",
               "Videos Counted", "Channel URL"]
    rows = [headers]
    for c in insights.get("top_channels", []):
        rows.append([
            c["channel"], c["avg_engagement_rate"], c["avg_views"],
            c["total_views"], c["video_count"], c["channel_url"],
        ])
    batch_update(sheets_svc, sheet_id,
                 [{"range": "Top Channels!A1", "values": rows}])
    format_header_row(sheets_svc, sheet_id, "Top Channels", len(headers))


def populate_rising_stars(sheets_svc, sheet_id: str, insights: dict):
    headers = ["Title", "Channel", "Views/Day", "Total Views", "Days Old",
               "Published", "URL"]
    rows = [headers]
    for v in insights.get("top_by_velocity", []):
        rows.append([
            v["title"], v["channel"], v.get("views_per_day") or "",
            v["views"], v.get("days_old") or "",
            (v.get("publish_date") or "")[:10], v["url"],
        ])
    batch_update(sheets_svc, sheet_id,
                 [{"range": "Rising Stars!A1", "values": rows}])
    format_header_row(sheets_svc, sheet_id, "Rising Stars", len(headers))


def populate_keywords(sheets_svc, sheet_id: str, insights: dict):
    headers = ["Keyword", "Frequency in Trending Titles"]
    rows = [headers] + [[k["word"], k["count"]] for k in insights.get("keywords", [])]
    batch_update(sheets_svc, sheet_id,
                 [{"range": "Keywords!A1", "values": rows}])
    format_header_row(sheets_svc, sheet_id, "Keywords", len(headers))


def populate_upload_timing(sheets_svc, sheet_id: str, insights: dict):
    by_day = insights.get("upload_by_day", {})
    by_hour = insights.get("upload_by_hour", {})

    day_rows = [["Day", "Upload Count"]] + [[d, c] for d, c in by_day.items()]
    hour_rows = [["Hour (UTC)", "Upload Count"]] + \
                [[f"{int(h):02d}:00", c] for h, c in by_hour.items()]

    batch_update(sheets_svc, sheet_id, [
        {"range": "Upload Timing!A1", "values": day_rows},
        {"range": "Upload Timing!D1", "values": hour_rows},
    ])
    format_header_row(sheets_svc, sheet_id, "Upload Timing", 5)


def main():
    from datetime import datetime
    insights = json.loads(INSIGHTS_PATH.read_text())
    month_year = datetime.now().strftime("%B %Y")

    print("Authenticating...")
    creds = get_creds()
    sheets_svc = build("sheets", "v4", credentials=creds)

    print("Creating Google Sheet...")
    sheet_id = create_sheet(sheets_svc, f"AI YouTube Insights — {month_year}")

    print("Populating tabs...")
    populate_summary(sheets_svc, sheet_id, insights)
    print("  ✓ Summary")
    populate_top_videos_views(sheets_svc, sheet_id, insights)
    print("  ✓ Top Videos (Views)")
    populate_top_videos_engagement(sheets_svc, sheet_id, insights)
    print("  ✓ Top Videos (Engagement)")
    populate_top_channels(sheets_svc, sheet_id, insights)
    print("  ✓ Top Channels")
    populate_rising_stars(sheets_svc, sheet_id, insights)
    print("  ✓ Rising Stars")
    populate_keywords(sheets_svc, sheet_id, insights)
    print("  ✓ Keywords")
    populate_upload_timing(sheets_svc, sheet_id, insights)
    print("  ✓ Upload Timing")

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    Path(".tmp/sheet_url.txt").write_text(url)
    print(f"\nSheet created → {url}")
    return url


if __name__ == "__main__":
    main()
