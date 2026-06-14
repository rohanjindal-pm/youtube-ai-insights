# Workflow: YouTube AI Insights Report

## Objective
Scrape YouTube for AI content relevant to a **technically sound AI Product Manager** — covering LLMs, deep learning, ML fundamentals, AI agents, RAG/embeddings, AI automation (n8n, Make, Zapier), and building AI products. Analyze engagement patterns and deliver a professional PDF report to the address set in `RECIPIENT_EMAIL` in `.env`.

**Target audience filter:** Content must be educational and technically substantive. **English-only** — Devanagari, Cyrillic, CJK, Arabic scripts and titles with 2+ foreign function words are rejected; English-titled videos that are clearly Hindi/Telugu/regional-language tutorials are also excluded via noise keywords. Also excluded: political content, entertainment/viral AI content, income/side-hustle content, and anything unrelated to understanding or building AI systems.

## Trigger
On-demand. Run when Rohan asks for an insights report.

## Required Setup (one-time)
- `APIFY_API_TOKEN` set in `.env`
- `credentials.json` in project root (Google OAuth Desktop App from Google Cloud Console)
- Python dependencies installed: `pip install apify-client google-api-python-client google-auth-httplib2 google-auth-oauthlib matplotlib seaborn wordcloud pandas python-dotenv`

## Execution Steps

Run these scripts in order from the project root, then invoke the Canvas Design skill:

```bash
python3 tools/scrape_youtube.py
python3 tools/analyze_data.py
python3 tools/generate_charts.py
# → Invoke canvas-design skill (see Step 4 below)
python3 tools/send_email.py
```

### Step 4: Generate PDF with Canvas Design Skill

After `generate_charts.py` completes, invoke the `canvas-design` skill to produce the PDF report.

**Inputs to pass to the skill:**
- Read `.tmp/insights.json` and extract all data fields before invoking
- Chart image paths: `.tmp/charts/top_videos_views.png`, `top_videos_engagement.png`, `channel_comparison.png`, `title_keywords.png`, `upload_heatmap.png`, `view_velocity.png`
- Output path: `.tmp/ai_insights_report.pdf`

**Design direction:**
- Professional dark-theme report — midnight navy backgrounds (`#1a1a2e`, `#0f3460`, `#16213e`), red accent (`#e94560`), cyan highlights (`#53c5e0`), light body text (`#eaeaea`), muted labels (`#a0a0c0`)
- Clean sans-serif typography, full-bleed section header bars, generous white space
- Data callout boxes for KPIs, embedded chart images sized to fill the page width

**PDF page structure (9 pages):**
1. **Cover** — "AI YouTube Insights Report", month/year subtitle, total videos analyzed as hero stat, key metrics row
2. **Executive Summary** — 4 KPI boxes (videos analyzed, avg engagement, total views, top video views) + top trending video callout + top creator callout
3. **Latest AI Technology Updates** — up to 7 recent announcement videos from the last 14 days, sorted by views; source field: `insights.json → latest_updates`
4. **LLMs & Foundation Models** — top 5 videos in recommended watch order (ranked by engagement × reach) + top 3 channels to follow; source: `insights.json → topic_groups["LLMs & Foundation Models"]`
5. **AI Agents & Orchestration** — same layout; source: `insights.json → topic_groups["AI Agents & Orchestration"]`
6. **RAG & AI Product Building** — same layout; source: `insights.json → topic_groups["RAG & AI Product Building"]`
7. **AI Automation & Workflows** — same layout; source: `insights.json → topic_groups["AI Automation & Workflows"]`
8. **Deep Learning & ML** — same layout; source: `insights.json → topic_groups["Deep Learning & ML"]`
9. **Strategic Recommendations** — 5 data-driven insights derived from `upload_by_day`, `keywords`, `topic_groups`, `top_channels`, `top_by_engagement`; no hardcoded content

## What Each Tool Does

| Tool | Input | Output | Notes |
|------|-------|--------|-------|
| `scrape_youtube.py` | APIFY_API_TOKEN | `.tmp/raw_videos.json` | ~2–3 min, costs ~$0.10–0.30 per run |
| `analyze_data.py` | raw_videos.json | `.tmp/insights.json` | Instant, pure Python |
| `generate_charts.py` | insights.json | `.tmp/charts/*.png` | 6 PNG files, ~10 sec |
| `canvas-design` skill | insights.json + charts | `.tmp/ai_insights_report.pdf` | 9-page professional PDF |
| `send_email.py` | insights.json + .pdf | Email sent | First run opens browser for Gmail auth |

## Edge Cases & Known Behaviors

**Apify rate limits:** If `scrape_youtube.py` fails mid-run, re-run it. Apify runs are idempotent — it creates a new actor run each time. Check Apify console if runs hang (>5 min).

**Gmail auth (first run):** `send_email.py` will open a browser window for OAuth consent. After approval, `token.json` is saved and future runs are automatic. If token expires (after ~1 year), delete `token.json` to re-auth.

**Missing chart files:** If `generate_charts.py` produces no charts (e.g. all chart data is empty), skip embedding that chart in the Canvas Design PDF and note it as unavailable. Check `insights.json` for empty arrays.

**Zero results from Apify:** If a search query returns 0 videos, the actor still succeeds — just no data for that query. Check `.tmp/raw_videos.json` for total video count. If total < 20, something is wrong with the Apify token or actor.

**Engagement rate threshold:** Videos with fewer than 10,000 views are excluded from engagement ranking to avoid outlier distortion.

## Output
- `.tmp/ai_insights_report.pdf` — 9-page professional PDF report
- Email delivered to `RECIPIENT_EMAIL` (set in `.env`) with HTML summary + .pdf attachment

## Estimated Cost
- Apify: ~$0.10–0.50 per run (8 search queries × 50 results + 10 channel deep-dives)
- Gmail API: Free
- Total runtime: ~3–5 minutes
