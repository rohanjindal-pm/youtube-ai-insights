"""
Generates chart PNG images from insights data.

Input:  .tmp/insights.json
Output: .tmp/charts/*.png (6 charts)
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import seaborn as sns
from wordcloud import WordCloud

# Color palette
BG = "#1a1a2e"
ACCENT1 = "#e94560"
ACCENT2 = "#0f3460"
ACCENT3 = "#16213e"
TEXT = "#eaeaea"
GRID = "#2a2a4e"

OUT_DIR = Path(".tmp/charts")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def apply_dark_style(fig, ax):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(ACCENT3)
    ax.tick_params(colors=TEXT, labelsize=9)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.grid(color=GRID, linewidth=0.5, alpha=0.7)


def truncate(s: str, n: int = 40) -> str:
    return s[:n] + "…" if len(s) > n else s


def fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def chart_top_videos_views(data: dict):
    videos = data["top_by_views"][:10]
    if not videos:
        print("  Skipping top_videos_views.png (no data)")
        return

    labels = [truncate(v["title"], 35) for v in videos]
    values = [v["views"] for v in videos]
    colors = [ACCENT1 if i == 0 else ACCENT2 for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], edgecolor="none", height=0.7)
    apply_dark_style(fig, ax)

    for bar, val in zip(bars, values[::-1]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                fmt_num(val), va="center", ha="left", color=TEXT, fontsize=8)

    ax.set_title("Top 10 Trending AI Videos by Views (Last 30 Days)", fontsize=13, pad=12, color=TEXT, fontweight="bold")
    ax.set_xlabel("Views", color=TEXT)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: fmt_num(int(x))))
    plt.tight_layout()
    fig.savefig(OUT_DIR / "top_videos_views.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  ✓ top_videos_views.png")


def chart_top_videos_engagement(data: dict):
    videos = data["top_by_engagement"][:10]
    if not videos:
        print("  Skipping top_videos_engagement.png (no data)")
        return

    labels = [truncate(v["title"], 35) for v in videos]
    values = [v["engagement_rate"] for v in videos]
    colors = [ACCENT1 if i == 0 else "#53c5e0" for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], edgecolor="none", height=0.7)
    apply_dark_style(fig, ax)

    for bar, val in zip(bars, values[::-1]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", ha="left", color=TEXT, fontsize=8)

    ax.set_title("Top 10 AI Videos by Engagement Rate (likes+comments / views)", fontsize=13, pad=12, color=TEXT, fontweight="bold")
    ax.set_xlabel("Engagement Rate (%)", color=TEXT)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "top_videos_engagement.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  ✓ top_videos_engagement.png")


def chart_channel_comparison(data: dict):
    channels = data["top_channels"][:8]
    if not channels:
        print("  Skipping channel_comparison.png (no data)")
        return

    labels = [truncate(c["channel"], 20) for c in channels]
    eng_rates = [c["avg_engagement_rate"] for c in channels]
    avg_views = [c["avg_views"] / 1000 for c in channels]  # in K

    x = np.arange(len(labels))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    bars1 = ax1.bar(x - width/2, eng_rates, width, color=ACCENT1, label="Avg Engagement %", alpha=0.9)
    bars2 = ax2.bar(x + width/2, avg_views, width, color="#53c5e0", label="Avg Views (K)", alpha=0.9)

    apply_dark_style(fig, ax1)
    ax2.set_facecolor(ACCENT3)
    ax2.tick_params(colors=TEXT, labelsize=9)
    ax2.yaxis.label.set_color(TEXT)
    for spine in ax2.spines.values():
        spine.set_edgecolor(GRID)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=30, ha="right", color=TEXT, fontsize=8)
    ax1.set_ylabel("Avg Engagement Rate (%)", color=TEXT)
    ax2.set_ylabel("Avg Views (K)", color=TEXT)

    p1 = mpatches.Patch(color=ACCENT1, label="Avg Engagement %")
    p2 = mpatches.Patch(color="#53c5e0", label="Avg Views (K)")
    ax1.legend(handles=[p1, p2], facecolor=ACCENT3, labelcolor=TEXT, fontsize=8, loc="upper right")

    ax1.set_title("Top Channels: Engagement Rate vs Avg Views", fontsize=13, pad=12, color=TEXT, fontweight="bold")
    fig.patch.set_facecolor(BG)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "channel_comparison.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  ✓ channel_comparison.png")


def chart_upload_heatmap(data: dict):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hours = list(range(24))

    # Build matrix: days × hours (using available data)
    by_day = data.get("upload_by_day", {})
    by_hour = data.get("upload_by_hour", {})

    # Create a simple proxy heatmap using day totals × hour distribution
    day_vals = np.array([by_day.get(d, 0) for d in days], dtype=float)
    hour_vals = np.array([by_hour.get(str(h), 0) for h in hours], dtype=float)

    if day_vals.sum() == 0 or hour_vals.sum() == 0:
        print("  Skipping upload_heatmap.png (no data)")
        return

    day_norm = day_vals / day_vals.sum()
    hour_norm = hour_vals / hour_vals.sum()
    matrix = np.outer(day_norm, hour_norm) * day_vals.sum()

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(
        matrix, ax=ax, cmap="RdYlGn", linewidths=0.3, linecolor=BG,
        xticklabels=[f"{h:02d}:00" if h % 3 == 0 else "" for h in hours],
        yticklabels=days,
        cbar_kws={"label": "Upload Frequency"},
    )
    ax.set_title("Upload Activity Heatmap (Day × Hour UTC)", fontsize=13, pad=12, color=TEXT, fontweight="bold")
    ax.tick_params(colors=TEXT, labelsize=8)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(ACCENT3)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "upload_heatmap.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  ✓ upload_heatmap.png")


def chart_title_keywords(data: dict):
    keywords = data.get("keywords", [])
    if not keywords:
        print("  Skipping title_keywords.png (no data)")
        return

    freq = {k["word"]: k["count"] for k in keywords}
    wc = WordCloud(
        width=1200, height=600, background_color=BG,
        colormap="RdYlGn", max_words=40, relative_scaling=0.5,
        prefer_horizontal=0.85,
    ).generate_from_frequencies(freq)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("Most Common Words in Trending AI Video Titles", fontsize=13, pad=12, color=TEXT, fontweight="bold")
    fig.patch.set_facecolor(BG)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "title_keywords.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  ✓ title_keywords.png")


def chart_view_velocity(data: dict):
    videos = [v for v in data.get("top_by_velocity", []) if v["views_per_day"] and v["days_old"]]
    if not videos:
        print("  Skipping view_velocity.png (no data)")
        return

    x = [v["days_old"] for v in videos]
    y = [v["views_per_day"] for v in videos]
    sizes = [max(30, v["views"] / 50_000) for v in videos]
    labels = [truncate(v["title"], 25) for v in videos]

    fig, ax = plt.subplots(figsize=(12, 6))
    scatter = ax.scatter(x, y, s=sizes, c=ACCENT1, alpha=0.8, edgecolors=ACCENT2, linewidth=0.8)

    for i, (xi, yi, label) in enumerate(zip(x, y, labels)):
        ax.annotate(label, (xi, yi), fontsize=7, color=TEXT,
                    xytext=(5, 5), textcoords="offset points", alpha=0.85)

    apply_dark_style(fig, ax)
    ax.set_title("View Velocity: Rising Stars (Views/Day vs Age)", fontsize=13, pad=12, color=TEXT, fontweight="bold")
    ax.set_xlabel("Days Since Published", color=TEXT)
    ax.set_ylabel("Views per Day", color=TEXT)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: fmt_num(int(x))))
    plt.tight_layout()
    fig.savefig(OUT_DIR / "view_velocity.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  ✓ view_velocity.png")


def main():
    data = json.loads(Path(".tmp/insights.json").read_text())
    print("Generating charts...")
    chart_top_videos_views(data)
    chart_top_videos_engagement(data)
    chart_channel_comparison(data)
    chart_upload_heatmap(data)
    chart_title_keywords(data)
    chart_view_velocity(data)
    print(f"\nAll charts saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
