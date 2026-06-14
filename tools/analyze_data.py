"""
Analyzes raw YouTube data to compute engagement metrics, trends, and insights.

Input:  .tmp/raw_videos.json
Output: .tmp/insights.json
"""

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Keywords that must appear in the TITLE for a video to pass the relevance filter.
# Description alone is not sufficient — prevents political/news videos with tangential AI mentions.
# Audience: technically sound AI Product Manager — needs LLMs, ML, agents, automation, AI products.
AI_TITLE_KEYWORDS = {
    # Core AI tools & models
    "claude", "chatgpt", "gpt", "gemini", "copilot", "openai", "anthropic",
    "mistral", "llama", "ollama", "perplexity", "deepseek",
    # Agents & orchestration frameworks
    "agent", "agents", "agentic", "crewai", "autogen", "langgraph", "langchain",
    "multi-agent", "mcp", "model context protocol",
    # Automation tools
    "n8n", "make.com", "zapier", "automation", "automate", "workflow",
    # LLMs & model fundamentals
    "llm", "llms", "large language model", "foundation model",
    "transformer", "attention mechanism", "tokenizer", "tokenization",
    "context window", "inference", "fine-tun", "fine tuning",
    # Deep learning & ML concepts
    "deep learning", "neural network", "machine learning",
    "backpropagation", "gradient descent", "diffusion model",
    # RAG, embeddings, vector
    "rag", "retrieval augmented", "vector database", "vector db",
    "embedding", "embeddings", "semantic search", "faiss", "pinecone", "weaviate",
    # Building & coding with AI
    "cursor", "vibe coding", "vibe-coding", "ai coding", "ai code",
    "prompt engineering", "prompting",
    # AI product & strategy
    "ai product", "ai pm", "ai product manager", "building with ai",
    "ai strategy", "generative ai", "local ai", "multimodal",
    # Generic compounds unambiguous in this context
    "ai agent", "ai automation", "ai workflow", "ai app", "ai tool", "ai tutorial",
    "ai explained", "ai course", "ai build", "ai stack",
    # Model evaluation & benchmarks
    "llm benchmark", "model benchmark", "model comparison", "evals",
    "llm evaluation",
}

NOISE_KEYWORDS = {
    # Politics & government — global
    "politics", "political", "election", "democrat", "republican",
    "trump", "biden", "harris", "obama", "modi", "congress", "parliament",
    "senate", "vote", "voting", "campaign", "governor", "legislation", "policy",
    "white house", "supreme court",
    # Indian political figures & parties
    "amit shah", "rahul gandhi", "kejriwal", "arvind kejriwal", "yogi adityanath",
    "smriti irani", "nitish kumar", "mamata", "priyanka gandhi", "bjp", "aap party",
    "aam aadmi", "shiv sena", "lok sabha", "rajya sabha", "cabinet minister",
    "home minister", "chief minister", "cm yogi",
    # News & current events
    "breaking news", "latest news", "today news", "headlines", "live news",
    "press conference", "news update", "current affairs",
    # War & geopolitics
    "war", "military", "army", "soldier", "weapon", "missile", "attack", "invasion",
    "ukraine", "russia", "israel", "hamas", "gaza", "conflict", "protest",
    "starlink frozen", "security concern",
    # Finance & unrelated markets
    "stock market", "stock tips", "mutual fund", "insurance",
    "bitcoin", "ethereum", "nft", "trading", "forex", "crypto trading",
    # Entertainment & lifestyle
    "nba", "nfl", "ipl", "cricket", "soccer", "football", "basketball",
    "recipe", "cooking", "makeup", "skincare", "fashion", "outfit",
    "celebrity", "kardashian", "drama", "gossip", "reality show",
    "prank", "roast",
    # Viral/reaction/entertainment AI content (not educational)
    "creepy glitch", "gone wrong", "turns into villain", "leaked last day",
    "chatgpt body", "chatgpt anomaly", "chatgpt aesthetic", "chatgpt epidemic",
    "ai body", "ai villain", "ai prank", "ai reaction", "ai meme",
    "you won't believe", "impossible confirmed", "cringe", "funny ai",
    # Income / side-hustle / get-rich content — not useful for an AI PM
    "passive income", "side hustle", "make money with ai", "make money using ai",
    "earn money with", "dropshipping", "faceless channel", "faceless youtube",
    "per month with ai", "per month with claude", "start earning",
    "ai influencer", "instagram with ai", "youtube shorts automation",
    "copy me", "just copy me", "if i had to start over", "halal ways to make",
    "most profitable", "get rich", "rich with ai", "rich using ai",
    "make you rich", "will make you rich", "7 will make",
    "= $", "/month with", "youtube =",  # income-claim title patterns like "= $62,000/Month"
    # Non-English language indicators (English-only policy)
    "telugu", "in tamil", "in kannada", "in malayalam", "in marathi",
    "in bangla", "in gujarati", "en español", "en français", "auf deutsch",
    # Hindi-content videos that use English-script titles
    "kaise banaye", "kaise bane", "kaise kare", "kaise sikhe",
    "in hindi", "hindi mein", "seekhiye",
    # Religion & spirituality
    "bhajan", "prayer", "sermon", "devotional", "pooja",
    # Health & unrelated wellness
    "weight loss", "diet", "fitness", "yoga", "meditation", "ayurveda",
    # Too academic / not actionable for AI PM
    "sanskrit",
}


def is_short(title: str, description: str) -> bool:
    combined = (title + " " + description).lower()
    return "#shorts" in combined or "#short" in combined or "youtube shorts" in combined


def jaccard_similarity(a: str, b: str) -> float:
    wa = set(re.findall(r"\b[a-zA-Z0-9]{2,}\b", a.lower()))
    wb = set(re.findall(r"\b[a-zA-Z0-9]{2,}\b", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def deduplicate_by_title(videos: list[dict], threshold: float = 0.75) -> list[dict]:
    kept = []
    for v in videos:
        if not any(jaccard_similarity(v["title"], k["title"]) >= threshold for k in kept):
            kept.append(v)
    return kept


# Words that strongly signal a non-English title. Two hits = reject.
# Covers Spanish, Portuguese, French, German, Russian romanisations.
_FOREIGN_WORDS = {
    # Spanish
    "de", "la", "el", "los", "las", "una", "que", "con", "del",
    "para", "como", "por", "este", "esta", "esto", "gratis",
    "curso", "cómo", "ahora", "más", "día", "año", "también",
    "inteligencia", "artificial", "aprende", "aprenda",
    "cambiado", "actualiza", "actualízate",
    # Portuguese
    "em", "dos", "com", "são", "você", "mais", "tem", "uma",
    "isso", "seu", "fazer", "assim", "muito", "aqui", "vamos",
    "nosso", "aula",
    # French (expanded — many titles only show 1 obvious word)
    "les", "des", "une", "sur", "est", "avec", "dans", "pour",
    "mon", "mes", "nos", "ses", "votre", "notre", "vous", "nous",
    "créer", "créez", "cette", "tout", "tous", "très", "aussi",
    "sans", "depuis", "avant", "après", "entre", "voici", "voilà",
    "ça", "cela", "donc", "comment",
    # German (expanded — many titles use "ich/mein/nicht" which were missing)
    "und", "ist", "mit", "das", "der", "die", "den", "ein",
    "eine", "auf", "für", "von", "ich", "mein", "meine", "meinen",
    "nicht", "haben", "werden", "können", "kein", "keine",
    "aber", "wenn", "oder", "wir", "sie", "sind", "lasse",
}


def _has_foreign_script(text: str) -> bool:
    """True if text contains characters from scripts that indicate a non-English language.
    Any single character from these blocks is enough to reject."""
    for c in text:
        cp = ord(c)
        if (
            0x0400 <= cp <= 0x04FF or  # Cyrillic
            0x0600 <= cp <= 0x06FF or  # Arabic
            0x0900 <= cp <= 0x097F or  # Devanagari (Hindi)
            0x0980 <= cp <= 0x09FF or  # Bengali
            0x0A80 <= cp <= 0x0AFF or  # Gujarati
            0x0B00 <= cp <= 0x0B7F or  # Odia
            0x0B80 <= cp <= 0x0BFF or  # Tamil
            0x0C00 <= cp <= 0x0C7F or  # Telugu
            0x0C80 <= cp <= 0x0CFF or  # Kannada
            0x0D00 <= cp <= 0x0D7F or  # Malayalam
            0x0E00 <= cp <= 0x0E7F or  # Thai
            0x1100 <= cp <= 0x11FF or  # Hangul Jamo (Korean)
            0x3040 <= cp <= 0x30FF or  # Hiragana + Katakana (Japanese)
            0x4E00 <= cp <= 0x9FFF or  # CJK Unified Ideographs
            0xAC00 <= cp <= 0xD7AF or  # Hangul Syllables (Korean)
            0xF900 <= cp <= 0xFAFF     # CJK Compatibility Ideographs
        ):
            return True
    return False


def is_english(title: str) -> bool:
    # Hard reject: any character from a non-Latin script → not English
    if _has_foreign_script(title):
        return False
    latin = sum(1 for c in title if c.isascii() and c.isalpha())
    other = sum(1 for c in title if not c.isascii() and c.isalpha())
    total_alpha = latin + other
    if total_alpha == 0:
        return True
    # Reject if >20% of alphabetic characters are accented non-ASCII
    # (a handful of accented chars in a mostly-ASCII title is fine for brand names)
    if other / total_alpha > 0.2:
        return False
    # Secondary check: 2+ known foreign function words = foreign language
    words = set(re.findall(r"\b[a-záéíóúãõçàüñèêëâùûïîôœæ]+\b", title.lower()))
    if len(words & _FOREIGN_WORDS) >= 2:
        return False
    return True


def is_relevant(title: str, description: str = "", channel: str = "") -> bool:
    if not is_english(title):
        return False
    # Reject if the channel name is in a non-Latin script — even if the title is translated
    # to English, the video content is almost certainly in that language.
    if _has_foreign_script(channel):
        return False
    if is_short(title, description):
        return False
    t = title.lower()
    # Noise check on title (description noise-check would be too aggressive for legitimate tutorials)
    if any(noise in t for noise in NOISE_KEYWORDS):
        return False
    # AI keyword must appear in the TITLE — description alone is not sufficient.
    # This prevents political/news videos whose descriptions tangentially mention AI.
    return any(kw in t for kw in AI_TITLE_KEYWORDS)


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "how", "what", "when", "where", "who", "why", "which", "this", "that",
    "these", "those", "i", "you", "he", "she", "it", "we", "they", "my",
    "your", "his", "her", "its", "our", "their", "using", "use", "get",
    "make", "new", "just", "like", "more", "also", "into", "about", "up",
    "not", "so", "if", "than", "then", "now", "only", "very", "full",
    "2024", "2025", "2026", "vs", "amp", "youtube", "video", "channel",
}

MIN_VIEWS_FOR_ENGAGEMENT = 10_000


def parse_int(val) -> int:
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    s = str(val).replace(",", "").strip()
    if s.endswith("K"):
        return int(float(s[:-1]) * 1_000)
    if s.endswith("M"):
        return int(float(s[:-1]) * 1_000_000)
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def parse_date(val) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(val)[:19], fmt[:len(str(val)[:19])]).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def normalize_video(v: dict) -> dict:
    views = parse_int(v.get("viewCount") or v.get("views"))
    likes = parse_int(v.get("likeCount") or v.get("likes"))
    comments = parse_int(v.get("commentCount") or v.get("comments"))
    pub_date = parse_date(v.get("publishDate") or v.get("uploadDate") or v.get("date"))

    now = datetime.now(timezone.utc)
    days_old = (now - pub_date).days if pub_date else None
    velocity = views / max(days_old, 1) if days_old is not None else None
    engagement = (likes + comments) / views * 100 if views >= MIN_VIEWS_FOR_ENGAGEMENT else None

    ch_handle = v.get("channelHandle", "")
    ch_url = (f"https://www.youtube.com/{ch_handle}" if ch_handle else
              v.get("channelUrl") or v.get("channel", {}).get("url", ""))

    return {
        "title": v.get("title", ""),
        "url": (v.get("url") or v.get("videoUrl") or
                (f"https://www.youtube.com/watch?v={v['id']}" if v.get("id") else "")),
        "channel": v.get("channelTitle") or v.get("channelName") or v.get("channel", {}).get("name", "Unknown"),
        "channel_url": ch_url,
        "views": views,
        "likes": likes,
        "comments": comments,
        "publish_date": pub_date.isoformat() if pub_date else None,
        "days_old": days_old,
        "thumbnail": v.get("thumbnailUrl") or v.get("thumbnail", ""),
        "engagement_rate": round(engagement, 3) if engagement is not None else None,
        "views_per_day": round(velocity, 1) if velocity is not None else None,
        "description": (v.get("description") or "")[:500],
        "source_query": v.get("_source_query", ""),
        "duration": v.get("duration", ""),
        "day_of_week": pub_date.strftime("%A") if pub_date else None,
        "hour_of_day": pub_date.hour if pub_date else None,
    }


def extract_keywords(titles: list[str]) -> list[dict]:
    words = []
    for title in titles:
        tokens = re.findall(r"\b[a-zA-Z]{3,}\b", title.lower())
        words.extend(t for t in tokens if t not in STOPWORDS)
    counts = Counter(words).most_common(30)
    return [{"word": w, "count": c} for w, c in counts]


# ── Topic classification ───────────────────────────────────────────────────────
# Ordered from most specific → most general so precise topics win over broad ones.
TOPIC_GROUPS = {
    "AI Agents & Orchestration": [
        "agent", "agents", "agentic", "multi-agent", "crewai", "autogen",
        "langgraph", "langchain", "mcp", "model context protocol",
        "autonomous agent", "agentic workflow", "build agent", "orchestrat",
    ],
    "AI Automation & Workflows": [
        "n8n", "zapier", "make.com", "no-code automation", "nocode automation",
        "workflow automation", "ai automation", "automate workflow",
        "automated pipeline",
    ],
    "RAG & AI Product Building": [
        "rag", "retrieval augmented", "vector database", "vector db",
        "embedding", "embeddings", "semantic search", "pinecone", "weaviate",
        "faiss", "prompt engineering", "fine-tun", "build with ai",
        "ai product", "cursor", "vibe coding", "llm api",
    ],
    "Deep Learning & ML": [
        "deep learning", "neural network", "machine learning",
        "backpropagation", "gradient descent", "diffusion model",
        "convolutional", "model training", "ml tutorial", "train a model",
    ],
    "LLMs & Foundation Models": [
        "llm", "llms", "large language model", "foundation model", "transformer",
        "how llm", "how gpt works", "how chatgpt works", "context window",
        "tokeniz", "model comparison", "benchmark", "model explained",
        "attention mechanism", "inference time", "pretraining", "multimodal",
        "claude vs", "gpt vs", "gemini vs", "model release",
    ],
}

ANNOUNCE_SIGNALS = [
    "introduc", "launch", "releas", "announc", "new model", "just dropped",
    "unveil", "reveal", "debut", "out now", "available now",
]


def classify_topic(video: dict) -> str | None:
    t = video["title"].lower()
    d = (video.get("description") or "")[:400].lower()

    best_topic, best_score = None, 0
    for topic, keywords in TOPIC_GROUPS.items():
        # Title keywords are 3× more definitive than description keywords.
        score = sum(3 for kw in keywords if kw in t) + sum(1 for kw in keywords if kw in d)
        if score > best_score:
            best_score = score
            best_topic = topic

    # Must have at least one title keyword hit — can't classify from description alone.
    if best_topic and any(kw in t for kw in TOPIC_GROUPS[best_topic]):
        return best_topic
    return None


def main():
    raw = json.loads(Path(".tmp/raw_videos.json").read_text())
    videos_raw = raw.get("videos", [])

    videos_all = [normalize_video(v) for v in videos_raw]

    # Step 1: language + noise + shorts + description relevance filter
    videos = [v for v in videos_all
              if is_relevant(v["title"], v.get("description", "") or "", v.get("channel", "") or "")]
    print(f"  Relevance filter: {len(videos_all)} → {len(videos)} videos ({len(videos_all) - len(videos)} removed)")

    # Step 2: deduplicate near-identical titles
    videos = deduplicate_by_title(videos)
    print(f"  Dedup filter:     kept {len(videos)} unique videos")

    videos_with_views = [v for v in videos if v["views"] > 0]

    # Top 10 by views (last 30 days)
    recent = [v for v in videos_with_views if v["days_old"] is not None and v["days_old"] <= 30]
    top_by_views = sorted(recent, key=lambda x: x["views"], reverse=True)[:10]

    # Top 10 by engagement rate
    engageable = [v for v in videos_with_views if v["engagement_rate"] is not None]
    top_by_engagement = sorted(engageable, key=lambda x: x["engagement_rate"], reverse=True)[:10]

    # Top 10 by view velocity
    has_velocity = [v for v in videos_with_views if v["views_per_day"] is not None]
    top_by_velocity = sorted(has_velocity, key=lambda x: x["views_per_day"], reverse=True)[:10]

    # Channel stats
    channel_map: dict[str, list] = {}
    for v in engageable:
        channel_map.setdefault(v["channel"], []).append(v)

    channel_stats = []
    for ch, vids in channel_map.items():
        avg_eng = sum(v["engagement_rate"] for v in vids) / len(vids)
        avg_views = sum(v["views"] for v in vids) / len(vids)
        channel_stats.append({
            "channel": ch,
            "channel_url": vids[0]["channel_url"],
            "video_count": len(vids),
            "avg_engagement_rate": round(avg_eng, 3),
            "avg_views": round(avg_views),
            "total_views": sum(v["views"] for v in vids),
        })
    top_channels = sorted(channel_stats, key=lambda x: x["avg_engagement_rate"], reverse=True)[:10]

    # Keyword frequency
    all_titles = [v["title"] for v in videos]
    keywords = extract_keywords(all_titles)

    # Upload timing
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = Counter(v["day_of_week"] for v in videos if v["day_of_week"])
    hour_counts = Counter(v["hour_of_day"] for v in videos if v["hour_of_day"] is not None)

    # Summary stats
    total_views = sum(v["views"] for v in videos_with_views)
    avg_engagement = (
        sum(v["engagement_rate"] for v in engageable) / len(engageable) if engageable else 0
    )

    # ── Topic groups ──────────────────────────────────────────────────────────
    topic_buckets: dict[str, list] = {t: [] for t in TOPIC_GROUPS}
    for v in videos:
        t = classify_topic(v)
        if t:
            topic_buckets[t].append(v)

    topic_groups = {}
    for topic, vids in topic_buckets.items():
        scoreable = [v for v in vids if v["views"] > 0]
        # Score: quality × reach — engagement weighted more than raw views
        top_vids = sorted(
            scoreable,
            key=lambda v: (v["engagement_rate"] or 0) * (v["views"] ** 0.3),
            reverse=True,
        )[:5]

        ch_eng: dict[str, list] = {}
        for v in [v for v in vids if v["engagement_rate"] is not None]:
            ch_eng.setdefault(v["channel"], []).append(v["engagement_rate"])
        ch_url_map = {v["channel"]: v["channel_url"] for v in vids}
        top_chs = sorted(
            [{"channel": ch, "channel_url": ch_url_map.get(ch, ""),
              "avg_engagement": round(sum(rates) / len(rates), 2),
              "video_count": len(rates)}
             for ch, rates in ch_eng.items()],
            key=lambda x: x["avg_engagement"], reverse=True,
        )[:3]

        topic_groups[topic] = {
            "top_videos": top_vids,
            "top_channels": top_chs,
            "total_videos": len(vids),
        }

    # ── Latest AI technology updates (last 14 days, announcement signals) ─────
    latest_updates = sorted(
        [v for v in videos_with_views
         if v["days_old"] is not None and v["days_old"] <= 14
         and any(sig in v["title"].lower() for sig in ANNOUNCE_SIGNALS)],
        key=lambda x: x["views"], reverse=True,
    )[:8]

    insights = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_videos_analyzed": len(videos),
            "total_views_across_all": total_views,
            "avg_engagement_rate": round(avg_engagement, 3),
            "top_creator": top_channels[0]["channel"] if top_channels else "N/A",
            "top_video_title": top_by_views[0]["title"] if top_by_views else "N/A",
            "top_video_views": top_by_views[0]["views"] if top_by_views else 0,
        },
        "top_by_views": top_by_views,
        "top_by_engagement": top_by_engagement,
        "top_by_velocity": top_by_velocity,
        "top_channels": top_channels,
        "topic_groups": topic_groups,
        "latest_updates": latest_updates,
        "keywords": keywords,
        "upload_by_day": {day: day_counts.get(day, 0) for day in day_order},
        "upload_by_hour": {str(h): hour_counts.get(h, 0) for h in range(24)},
    }

    Path(".tmp/insights.json").write_text(json.dumps(insights, indent=2))
    print(f"Insights saved → .tmp/insights.json")
    print(f"  Videos analyzed: {len(videos)}")
    print(f"  Avg engagement:  {avg_engagement:.2f}%")
    print(f"  Top creator:     {insights['summary']['top_creator']}")


if __name__ == "__main__":
    main()
