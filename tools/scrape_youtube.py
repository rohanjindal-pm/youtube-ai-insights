"""
Scrapes YouTube for AI niche content using Apify actors.

Phase A: Keyword search via api-ninja/youtube-search-scraper
Phase B: Top channel deep-dive via streamers/youtube-channel-scraper

Output: .tmp/raw_videos.json
"""

import json
import os
import time
from pathlib import Path

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

SEARCH_QUERIES = [
    # Claude & Anthropic
    "Claude AI tutorial 2026",
    "Claude API build tutorial",
    "Anthropic Claude agents tutorial",

    # AI Agents & orchestration frameworks
    "AI agents tutorial 2026",
    "build AI agent from scratch 2026",
    "agentic AI workflow tutorial 2026",
    "multi-agent systems tutorial 2026",
    "LangGraph tutorial 2026",
    "CrewAI tutorial 2026",

    # AI Automation
    "n8n AI automation tutorial 2026",
    "AI workflow automation tutorial 2026",
    "no code AI automation 2026",

    # LLMs & Foundation Models — how they work
    "how LLMs work explained 2026",
    "large language model explained 2026",
    "transformer model explained 2026",
    "foundation models tutorial 2026",

    # Deep Learning & Machine Learning concepts
    "deep learning explained 2026",
    "machine learning tutorial 2026",
    "neural network explained 2026",
    "fine-tuning LLM tutorial 2026",

    # RAG, embeddings, vector databases
    "RAG tutorial 2026",
    "retrieval augmented generation tutorial",
    "vector database tutorial 2026",
    "embeddings tutorial LLM 2026",

    # Building AI products & prompt engineering
    "prompt engineering tutorial 2026",
    "building AI product tutorial 2026",
    "AI product management 2026",
    "LLM API integration tutorial 2026",

    # Model comparisons & benchmarks
    "Claude vs GPT vs Gemini 2026",
    "LLM benchmark comparison 2026",
]

MAX_RESULTS_PER_QUERY = 50
TOP_CHANNELS_COUNT = 10


def run_search(client: ApifyClient, query: str) -> list[dict]:
    print(f"  Searching: {query}")
    run = client.actor("api-ninja/youtube-search-scraper").call(
        run_input={
            "query": query,
            "maxResults": MAX_RESULTS_PER_QUERY,
            "sortBy": "popularity",
            "uploadDate": "month",
            "type": "video",
            "videoDepthDetails": "standard",
        }
    )
    dataset_id = run.default_dataset_id if hasattr(run, "default_dataset_id") else run["defaultDatasetId"]
    items = list(client.dataset(dataset_id).iterate_items())
    print(f"    → {len(items)} videos")
    return items


def run_channel_deep_dive(client: ApifyClient, channel_urls: list[str]) -> list[dict]:
    print(f"\nDeep-diving {len(channel_urls)} top channels...")
    run = client.actor("streamers/youtube-channel-scraper").call(
        run_input={
            "startUrls": [{"url": u} for u in channel_urls],
            "maxResults": 20,
            "sortVideosBy": "POPULAR",
        }
    )
    dataset_id = run.default_dataset_id if hasattr(run, "default_dataset_id") else run["defaultDatasetId"]
    items = list(client.dataset(dataset_id).iterate_items())
    print(f"  → {len(items)} channel records")
    return items


def main():
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token or api_token == "your_apify_api_token_here":
        raise ValueError("Set APIFY_API_TOKEN in .env")

    client = ApifyClient(api_token)
    Path(".tmp/charts").mkdir(parents=True, exist_ok=True)

    # Phase A: keyword searches
    all_videos = []
    print("Phase A: Keyword searches")
    for query in SEARCH_QUERIES:
        videos = run_search(client, query)
        for v in videos:
            v["_source_query"] = query
        all_videos.extend(videos)
        time.sleep(1)  # be polite

    # Deduplicate by video ID
    seen_ids = set()
    unique_videos = []
    for v in all_videos:
        vid_id = v.get("id") or v.get("videoId") or v.get("url", "")
        if vid_id not in seen_ids:
            seen_ids.add(vid_id)
            unique_videos.append(v)

    print(f"\nTotal unique videos: {len(unique_videos)}")

    # Phase B: top channel deep-dive
    channel_counts: dict[str, int] = {}
    channel_urls: dict[str, str] = {}
    for v in unique_videos:
        ch_name = v.get("channelTitle") or v.get("channelName") or v.get("channel", {}).get("name", "")
        ch_handle = v.get("channelHandle", "")
        ch_url = (f"https://www.youtube.com/{ch_handle}" if ch_handle else
                  v.get("channelUrl") or v.get("channel", {}).get("url", ""))
        if ch_name and ch_url:
            channel_counts[ch_name] = channel_counts.get(ch_name, 0) + 1
            channel_urls[ch_name] = ch_url

    top_channels = sorted(channel_counts, key=lambda x: channel_counts[x], reverse=True)[
        :TOP_CHANNELS_COUNT
    ]
    top_channel_urls = [channel_urls[ch] for ch in top_channels if ch in channel_urls]

    channel_data = []
    if top_channel_urls:
        channel_data = run_channel_deep_dive(client, top_channel_urls)

    output = {
        "videos": unique_videos,
        "channels": channel_data,
        "queries": SEARCH_QUERIES,
        "top_channel_names": top_channels,
    }

    out_path = Path(".tmp/raw_videos.json")
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nSaved {len(unique_videos)} videos + {len(channel_data)} channel records → {out_path}")


if __name__ == "__main__":
    main()
