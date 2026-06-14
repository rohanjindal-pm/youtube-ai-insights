"""
Signal Noir — AI YouTube Insights PDF
7 pages: Cover → Latest AI Updates → 5 Topic Group pages.
Each topic page: best channels (clickable) + top 5 videos with full titles and watch links.
"""

import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE     = Path(__file__).parent.parent
INSIGHTS = BASE / ".tmp/insights.json"
OUT_PDF  = BASE / ".tmp/ai_insights_report.pdf"

with open(INSIGHTS) as f:
    D = json.load(f)

S        = D["summary"]
TOPICS   = D.get("topic_groups", {})
LATEST   = D.get("latest_updates", [])
CHANNELS = D.get("top_channels", [])
BY_VIEWS = D.get("top_by_views", [])
MONTH    = datetime.now().strftime("%B %Y")

TOPIC_ORDER = [
    "LLMs & Foundation Models",
    "AI Agents & Orchestration",
    "RAG & AI Product Building",
    "AI Automation & Workflows",
    "Deep Learning & ML",
]
TOTAL_PG = 2 + len(TOPIC_ORDER)

# ── Fonts ──────────────────────────────────────────────────────────────────────
SYS = "/System/Library/Fonts"
SUP = f"{SYS}/Supplemental"

def reg(name, path):
    pdfmetrics.registerFont(TTFont(name, path))

reg("SF",      f"{SYS}/SFNS.ttf")
reg("VerdanaB",f"{SUP}/Verdana Bold.ttf")
reg("Verdana", f"{SUP}/Verdana.ttf")
reg("ArialB",  f"{SUP}/Arial Bold.ttf")
reg("Arial",   f"{SUP}/Arial.ttf")
reg("AndMono", f"{SUP}/Andale Mono.ttf")

# ── Palette ────────────────────────────────────────────────────────────────────
BG    = colors.HexColor("#0d1117")
PANEL = colors.HexColor("#1a1a2e")
PAN2  = colors.HexColor("#0f3460")
RED   = colors.HexColor("#e94560")
CYAN  = colors.HexColor("#53c5e0")
BODY  = colors.HexColor("#eaeaea")
MUTED = colors.HexColor("#a0a0c0")
WHITE = colors.white
RULE  = colors.HexColor("#2a2a4e")

W, H = letter
M    = 36

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt(n):
    n = int(n or 0)
    if n >= 1_000_000_000: return f"{n/1e9:.1f}B"
    if n >= 1_000_000:     return f"{n/1e6:.1f}M"
    if n >= 1_000:         return f"{n/1e3:.0f}K"
    return str(n)

def trunc(s, n):
    s = s or ""
    return s[:n] + "…" if len(s) > n else s

def wrap_text(text, font_name, font_size, max_width):
    """Break text into lines that fit within max_width. Returns list of strings."""
    words = (text or "").split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip() if current else word
        if pdfmetrics.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]

def add_link(c, url, x, y, w, h):
    if url:
        c.linkURL(url, (x, y, x + w, y + h), relative=0)

def fill_bg(c):
    c.setFillColor(BG); c.rect(0, 0, W, H, fill=1, stroke=0)

def hrule(c, y, col=None, lw=0.4):
    c.setStrokeColor(col or RULE); c.setLineWidth(lw)
    c.line(M, y, W - M, y)

def footer(c):
    c.setFillColor(PAN2); c.rect(0, 0, W, 26, fill=1, stroke=0)
    c.setFillColor(RED);  c.rect(0, 26, W, 0.5, fill=1, stroke=0)
    c.setFillColor(MUTED); c.setFont("AndMono", 7)
    c.drawCentredString(W/2, 9, f"AI YOUTUBE INSIGHTS  ·  {MONTH.upper()}  ·  FOR THE TECHNICALLY SOUND AI PM")

def header_band(c, label, page_num):
    bh = 50; top = H - bh
    c.setFillColor(PAN2); c.rect(0, top, W, bh, fill=1, stroke=0)
    c.setFillColor(RED);  c.rect(0, top, 5, bh, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("VerdanaB", 13)
    c.drawString(M + 8, top + 16, label.upper())
    c.setFillColor(MUTED); c.setFont("AndMono", 8.5)
    c.drawRightString(W - M, top + 18, f"{page_num:02d} / {TOTAL_PG:02d}")
    c.setStrokeColor(RED); c.setLineWidth(0.5)
    c.line(0, top, W, top)

# ── Video row (used on topic pages and latest-updates page) ───────────────────
RANK_W   = 44   # space for rank number
BTN_W    = 58   # "▶ WATCH" button width
BTN_H    = 18
TEXT_X   = M + RANK_W          # where title/channel text starts
TEXT_MAX = W - M - RANK_W - BTN_W - 12   # max width for title text
ROW_H    = 80   # fixed row height; accommodates 2-line titles

def draw_video_row(c, y, rank, title, channel, channel_url, video_url, engagement):
    """Draw one video row starting at y (bottom of row = y, top = y + ROW_H)."""
    title_font, title_sz = "VerdanaB", 10.5
    ch_font,    ch_sz    = "Arial",    8.5

    lines = wrap_text(title, title_font, title_sz, TEXT_MAX)[:2]  # max 2 lines

    # Vertical positioning within the row (measured from row bottom)
    if len(lines) == 1:
        title_y = y + ROW_H - 22
        ch_y    = y + ROW_H - 38
    else:
        title_y = y + ROW_H - 18
        ch_y    = y + ROW_H - 46

    # Rank badge
    c.setFillColor(RED); c.setFont("AndMono", 22)
    c.drawString(M, y + ROW_H - 30, f"{rank:02d}")

    # Title lines (clickable)
    c.setFillColor(WHITE); c.setFont(title_font, title_sz)
    for i, line in enumerate(lines):
        ly = title_y - i * 16
        c.drawString(TEXT_X, ly, line)
        lw = pdfmetrics.stringWidth(line, title_font, title_sz)
        add_link(c, video_url, TEXT_X, ly - 2, lw, title_sz + 4)

    # Channel name (clickable, underlined)
    ch_display = channel or ""
    c.setFillColor(CYAN); c.setFont(ch_font, ch_sz)
    c.drawString(TEXT_X, ch_y, ch_display)
    ch_w = pdfmetrics.stringWidth(ch_display, ch_font, ch_sz)
    c.setStrokeColor(CYAN); c.setLineWidth(0.4)
    c.line(TEXT_X, ch_y - 1, TEXT_X + ch_w, ch_y - 1)
    add_link(c, channel_url, TEXT_X, ch_y - 2, ch_w, ch_sz + 4)

    # Engagement rate
    if engagement:
        c.setFillColor(MUTED); c.setFont("AndMono", 7.5)
        c.drawRightString(W - M, ch_y, f"{engagement:.2f}% eng")

    # ▶ WATCH button
    btn_x = W - M - BTN_W
    btn_y = y + ROW_H - 28
    c.setFillColor(RED); c.roundRect(btn_x, btn_y, BTN_W, BTN_H, 3, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("ArialB", 7.5)
    c.drawCentredString(btn_x + BTN_W / 2, btn_y + 5, "▶ WATCH")
    add_link(c, video_url, btn_x, btn_y, BTN_W, BTN_H)

    hrule(c, y + 4)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1: COVER
# ─────────────────────────────────────────────────────────────────────────────
c = rl_canvas.Canvas(str(OUT_PDF), pagesize=letter)
c.setTitle(f"AI YouTube Insights — {MONTH}")
fill_bg(c)

c.setStrokeColor(colors.HexColor("#1a1a3e")); c.setLineWidth(0.4)
for gx in range(0, int(W)+1, 72): c.line(gx, 0, gx, H)
for gy in range(0, int(H)+1, 72): c.line(0, gy, W, gy)

c.setFillColor(RED); c.rect(0, H - 5, W, 5, fill=1, stroke=0)
c.setFillColor(MUTED); c.setFont("AndMono", 9)
c.drawString(M, H - 36, f"AUTOMATED INTELLIGENCE REPORT  ·  {MONTH.upper()}")
hrule(c, H - 44, RED, lw=0.5)

c.setFillColor(WHITE); c.setFont("VerdanaB", 52)
c.drawString(M, H - 116, "AI YouTube")
c.setFillColor(RED); c.drawString(M, H - 176, "Insights")
c.setFillColor(MUTED); c.setFont("SF", 12)
c.drawString(M, H - 208, f"Topic-grouped intelligence for the technically sound AI PM  ·  {MONTH}")

hy = 322
c.setFillColor(PANEL); c.rect(M, hy, W - 2*M, 136, fill=1, stroke=0)
c.setFillColor(RED);   c.rect(M, hy + 133, W - 2*M, 3, fill=1, stroke=0)
c.setFillColor(RED);   c.setFont("AndMono", 64)
c.drawCentredString(W/2, hy + 66, str(S["total_videos_analyzed"]))
c.setFillColor(MUTED); c.setFont("Arial", 11)
c.drawCentredString(W/2, hy + 46, "AI VIDEOS ANALYZED")

sw = (W - 2*M) / 3
for i, (val, lbl) in enumerate([
    (fmt(S["total_views_across_all"]), "TOTAL VIEWS"),
    (f'{S["avg_engagement_rate"]:.2f}%', "AVG ENGAGEMENT"),
    (str(len(TOPIC_ORDER)), "TOPIC GROUPS"),
]):
    sx = M + i * sw
    c.setFillColor(PAN2); c.rect(sx + 4, hy - 50, sw - 8, 42, fill=1, stroke=0)
    c.setFillColor(CYAN); c.setFont("AndMono", 16)
    c.drawCentredString(sx + sw/2, hy - 22, val)
    c.setFillColor(MUTED); c.setFont("Arial", 7)
    c.drawCentredString(sx + sw/2, hy - 36, lbl)

c.setFillColor(PAN2); c.rect(0, 0, W, 32, fill=1, stroke=0)
c.setFillColor(RED);  c.rect(0, 32, W, 1, fill=1, stroke=0)
c.setFillColor(MUTED); c.setFont("AndMono", 7.5)
c.drawCentredString(W/2, 12, "POWERED BY YOUTUBE AI INSIGHTS AUTOMATION")
c.showPage()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2: LATEST AI TECHNOLOGY UPDATES
# ─────────────────────────────────────────────────────────────────────────────
fill_bg(c)
header_band(c, "Latest AI Technology Updates", 2)

c.setFillColor(MUTED); c.setFont("Arial", 8.5)
c.drawString(M, H - 68, "Most-viewed AI announcement & launch videos from the last 14 days")
hrule(c, H - 76, RED, lw=0.5)

if LATEST:
    ry = H - 82
    for v in LATEST[:7]:
        ry -= ROW_H
        draw_video_row(c, ry,
            rank        = LATEST.index(v) + 1,
            title       = v.get("title", ""),
            channel     = v.get("channel", ""),
            channel_url = v.get("channel_url", ""),
            video_url   = v.get("url", ""),
            engagement  = v.get("engagement_rate"),
        )
        # Days-old badge (overdraws rank area)
        days = v.get("days_old", 0)
        bw = 46
        c.setFillColor(PAN2); c.roundRect(M, ry + ROW_H - 28, bw, 20, 4, fill=1, stroke=0)
        c.setFillColor(CYAN); c.setFont("AndMono", 8)
        c.drawCentredString(M + bw/2, ry + ROW_H - 21, f"{days}d ago")
else:
    c.setFillColor(MUTED); c.setFont("Arial", 10)
    c.drawCentredString(W/2, H/2, "No announcement videos found in the last 14 days.")
    c.setFont("Arial", 8.5)
    c.drawCentredString(W/2, H/2 - 18, "Run a fresh scrape to populate this section.")

footer(c); c.showPage()

# ─────────────────────────────────────────────────────────────────────────────
# PAGES 3–7: TOPIC GROUP PAGES
# ─────────────────────────────────────────────────────────────────────────────
for pg_offset, topic in enumerate(TOPIC_ORDER):
    page_num = 3 + pg_offset
    group    = TOPICS.get(topic, {"top_videos": [], "top_channels": [], "total_videos": 0})
    vids     = group.get("top_videos", [])
    chs      = group.get("top_channels", [])
    total    = group.get("total_videos", 0)

    fill_bg(c)
    header_band(c, topic, page_num)

    content_top = H - 56

    # ── TOP CHANNELS ──────────────────────────────────────────────────────────
    ch_label_y  = content_top - 20
    c.setFillColor(RED);  c.setFont("ArialB", 7.5)
    c.drawString(M, ch_label_y, "TOP CHANNELS TO FOLLOW")
    c.setFillColor(MUTED); c.setFont("Arial", 7.5)
    c.drawRightString(W - M, ch_label_y, f"{total} videos in this category")

    CH_H       = 62
    ch_card_y  = ch_label_y - 10 - CH_H

    if chs:
        n_cards = min(len(chs), 3)
        cw = (W - 2*M - (n_cards - 1) * 10) / n_cards
        for j, ch_data in enumerate(chs[:3]):
            cx = M + j * (cw + 10)
            cy = ch_card_y
            c.setFillColor(PANEL); c.roundRect(cx, cy, cw, CH_H, 5, fill=1, stroke=0)
            c.setFillColor(CYAN);  c.rect(cx, cy + CH_H - 3, cw, 3, fill=1, stroke=0)
            # Channel name (full, centered, wraps to 2 lines if needed)
            ch_name = ch_data.get("channel", "")
            ch_lines = wrap_text(ch_name, "ArialB", 8, cw - 12)[:2]
            name_y = cy + CH_H - 16
            c.setFillColor(BODY); c.setFont("ArialB", 8)
            for li, ln in enumerate(ch_lines):
                c.drawCentredString(cx + cw/2, name_y - li * 11, ln)
            # Engagement stat
            c.setFillColor(RED); c.setFont("AndMono", 17)
            c.drawCentredString(cx + cw/2, cy + 22, f"{ch_data['avg_engagement']:.1f}%")
            c.setFillColor(MUTED); c.setFont("Arial", 6)
            c.drawCentredString(cx + cw/2, cy + 10, "AVG ENGAGEMENT")
            # Make entire card clickable
            ch_url = ch_data.get("channel_url", "")
            add_link(c, ch_url, cx, cy, cw, CH_H)
    else:
        c.setFillColor(MUTED); c.setFont("Arial", 8.5)
        c.drawString(M, ch_card_y + 20, "No channel data yet — re-scrape to populate.")

    # ── WATCH ORDER ───────────────────────────────────────────────────────────
    videos_top = ch_card_y - 18
    hrule(c, videos_top + 2, RED, lw=0.5)
    c.setFillColor(RED); c.setFont("ArialB", 7.5)
    c.drawString(M, videos_top - 12, "RECOMMENDED WATCH ORDER")
    c.setFillColor(MUTED); c.setFont("Arial", 7.5)
    c.drawRightString(W - M, videos_top - 12, "ranked by engagement × reach")

    if vids:
        vy = videos_top - 24
        for i, v in enumerate(vids[:5]):
            vy -= ROW_H
            draw_video_row(c, vy,
                rank        = i + 1,
                title       = v.get("title", ""),
                channel     = v.get("channel", ""),
                channel_url = v.get("channel_url", ""),
                video_url   = v.get("url", ""),
                engagement  = v.get("engagement_rate"),
            )
    else:
        c.setFillColor(MUTED); c.setFont("Arial", 9)
        c.drawString(M, videos_top - 52, "No videos in this category yet.")
        c.setFont("Arial", 8)
        c.drawString(M, videos_top - 68, "Run a fresh scrape with the updated queries to populate.")

    footer(c); c.showPage()

c.save()
print(f"PDF saved → {OUT_PDF}")
print(f"Pages: {TOTAL_PG}  ·  Size: {OUT_PDF.stat().st_size / 1024:.0f} KB")
