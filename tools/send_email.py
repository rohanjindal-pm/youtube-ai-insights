"""
Sends the AI insights PDF report via Gmail using OAuth2.

Requires credentials.json in the project root (Google Cloud OAuth desktop app).
token.json is created automatically after first auth.

Input:  .tmp/ai_insights_report.pdf + .tmp/insights.json + .tmp/sheet_url.txt
Output: Email sent to RECIPIENT_EMAIL
"""

import base64
import json
import os
import sys
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
if not RECIPIENT_EMAIL:
    raise ValueError("Set RECIPIENT_EMAIL in .env")
CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")
PDF_PATH = Path(".tmp/ai_insights_report.pdf")
INSIGHTS_PATH = Path(".tmp/insights.json")
SHEET_URL_PATH = Path(".tmp/sheet_url.txt")


def get_gmail_service():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(
                    "ERROR: credentials.json not found.\n"
                    "Download it from Google Cloud Console → APIs & Services → Credentials\n"
                    "(Create OAuth 2.0 Client ID → Desktop app → Download JSON → save as credentials.json)"
                )
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())
        print("Gmail auth token saved → token.json")

    return build("gmail", "v1", credentials=creds)


def build_html_body(insights: dict, sheet_url: str = "") -> str:
    s = insights["summary"]
    top_videos = insights.get("top_by_views", [])[:3]
    top_channels = insights.get("top_channels", [])[:3]
    month_year = datetime.now().strftime("%B %Y")

    def fmt(n):
        n = int(n or 0)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.0f}K"
        return str(n)

    video_rows = "".join(
        f"<tr><td style='padding:6px 12px;color:#eaeaea;border-bottom:1px solid #2a2a4e'>{v['title'][:60]}</td>"
        f"<td style='padding:6px 12px;color:#e94560;text-align:right;border-bottom:1px solid #2a2a4e'>{fmt(v['views'])}</td></tr>"
        for v in top_videos
    )

    channel_rows = "".join(
        f"<tr><td style='padding:6px 12px;color:#eaeaea;border-bottom:1px solid #2a2a4e'>{c['channel']}</td>"
        f"<td style='padding:6px 12px;color:#53c5e0;text-align:right;border-bottom:1px solid #2a2a4e'>{c['avg_engagement_rate']:.2f}%</td></tr>"
        for c in top_channels
    )

    return f"""
<html>
<body style="background:#1a1a2e;font-family:Arial,sans-serif;padding:32px;color:#eaeaea;">
  <div style="max-width:640px;margin:0 auto;">
    <div style="background:#0f3460;padding:24px 32px;border-radius:8px 8px 0 0;border-bottom:4px solid #e94560;">
      <h1 style="margin:0;color:#ffffff;font-size:24px;">📊 AI YouTube Insights</h1>
      <p style="margin:6px 0 0;color:#a0a0c0;font-size:13px;">{month_year} · Automated Report</p>
    </div>

    <div style="background:#16213e;padding:24px 32px;">
      <h2 style="color:#e94560;font-size:15px;margin:0 0 16px;">Key Metrics</h2>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:12px;background:#1a1a2e;border-radius:6px;text-align:center;margin:4px;">
            <div style="font-size:22px;font-weight:bold;color:#e94560;">{fmt(s['total_videos_analyzed'])}</div>
            <div style="font-size:11px;color:#a0a0c0;">Videos Analyzed</div>
          </td>
          <td style="padding:4px;"></td>
          <td style="padding:12px;background:#1a1a2e;border-radius:6px;text-align:center;">
            <div style="font-size:22px;font-weight:bold;color:#e94560;">{s['avg_engagement_rate']:.2f}%</div>
            <div style="font-size:11px;color:#a0a0c0;">Avg Engagement</div>
          </td>
          <td style="padding:4px;"></td>
          <td style="padding:12px;background:#1a1a2e;border-radius:6px;text-align:center;">
            <div style="font-size:22px;font-weight:bold;color:#e94560;">{fmt(s['total_views_across_all'])}</div>
            <div style="font-size:11px;color:#a0a0c0;">Total Views</div>
          </td>
        </tr>
      </table>

      <h2 style="color:#e94560;font-size:15px;margin:24px 0 12px;">🔥 Top Trending Videos</h2>
      <table style="width:100%;border-collapse:collapse;background:#1a1a2e;border-radius:6px;">
        <tr style="background:#0f3460;">
          <th style="padding:8px 12px;text-align:left;color:#a0a0c0;font-size:12px;">Title</th>
          <th style="padding:8px 12px;text-align:right;color:#a0a0c0;font-size:12px;">Views</th>
        </tr>
        {video_rows}
      </table>

      <h2 style="color:#e94560;font-size:15px;margin:24px 0 12px;">🏆 Top Channels by Engagement</h2>
      <table style="width:100%;border-collapse:collapse;background:#1a1a2e;border-radius:6px;">
        <tr style="background:#0f3460;">
          <th style="padding:8px 12px;text-align:left;color:#a0a0c0;font-size:12px;">Channel</th>
          <th style="padding:8px 12px;text-align:right;color:#a0a0c0;font-size:12px;">Avg Engagement</th>
        </tr>
        {channel_rows}
      </table>

      {'<div style="margin-top:24px;padding:16px;background:#1a1a2e;border-radius:6px;border-left:4px solid #e94560;">' +
       f'<p style="margin:0 0 8px;color:#eaeaea;font-size:13px;font-weight:bold;">📊 Full Data in Google Sheets</p>' +
       f'<a href="{sheet_url}" style="color:#53c5e0;font-size:12px;word-break:break-all;">{sheet_url}</a>' +
       '</div>' if sheet_url else ''}

      <p style="color:#a0a0c0;font-size:12px;margin-top:24px;">
        Full report attached. Open the PDF for charts, channel analysis, keyword trends, and strategic recommendations.
      </p>
    </div>

    <div style="background:#0f3460;padding:16px 32px;border-radius:0 0 8px 8px;text-align:center;">
      <p style="margin:0;color:#a0a0c0;font-size:11px;">Generated automatically · YouTube AI Insights Automation</p>
    </div>
  </div>
</body>
</html>
"""


def main():
    if not PDF_PATH.exists():
        print(f"ERROR: {PDF_PATH} not found. Run the canvas-design skill first.")
        sys.exit(1)

    if not INSIGHTS_PATH.exists():
        print(f"ERROR: {INSIGHTS_PATH} not found. Run analyze_data.py first.")
        sys.exit(1)

    insights = json.loads(INSIGHTS_PATH.read_text())
    sheet_url = SHEET_URL_PATH.read_text().strip() if SHEET_URL_PATH.exists() else ""
    month_year = datetime.now().strftime("%B %Y")

    print("Authenticating with Gmail...")
    service = get_gmail_service()

    msg = MIMEMultipart("mixed")
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = f"📊 AI YouTube Insights Report — {month_year}"

    html_body = build_html_body(insights, sheet_url)
    msg.attach(MIMEText(html_body, "html"))

    pdf_data = PDF_PATH.read_bytes()
    attachment = MIMEApplication(pdf_data, _subtype="pdf")
    filename = f"AI_YouTube_Insights_{datetime.now().strftime('%Y_%m')}.pdf"
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

    print(f"Email sent to {RECIPIENT_EMAIL}")
    print(f"  Subject: 📊 AI YouTube Insights Report — {month_year}")
    print(f"  Attachment: {filename} ({len(pdf_data) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
