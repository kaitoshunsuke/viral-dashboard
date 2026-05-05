import os
import re
import json
import datetime
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

CACHE_FILE = Path(__file__).parent / "cache.json"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# クォータコスト: videos.list=1pt, search.list=100pt → videos.listのみ使用
OVERSEAS_REGIONS = ["US", "GB", "KR", "FR", "DE"]
JAPAN_REGION = "JP"

BEAUTY_GENRES = {
    "product_pr":    {"label": "商品PR・レビュー",      "keywords": ["review", "unboxing", "haul", "try", "testing", "worth it", "honest", "レビュー", "開封"]},
    "skincare":      {"label": "スキンケア",             "keywords": ["skincare", "skin care", "serum", "moisturizer", "spf", "routine", "glass skin", "スキンケア", "美肌"]},
    "makeup":        {"label": "メイク・コスメ",         "keywords": ["makeup", "cosmetic", "lipstick", "foundation", "eyeshadow", "grwm", "look", "メイク", "コスメ"]},
    "influencer":    {"label": "インフルエンサーPR",     "keywords": ["vlog", "haul", "grwm", "my routine", "get ready", "collab", "案件", "コラボ"]},
    "campaign":      {"label": "キャンペーン・新発売",   "keywords": ["new", "launch", "limited", "collection", "release", "drop", "新発売", "限定"]},
    "entertainment": {"label": "エンタメ・バズ動画",     "keywords": ["transformation", "challenge", "glow up", "before after", "satisfying", "viral", "変身", "ビフォー"]},
}

# 美容関連の大カテゴリID（Beauty & Fashion = 26 に近いもの）
BEAUTY_CATEGORY_IDS = ["26", "22", "24", "10"]  # HowTo, People, Entertainment, Music


def _parse_duration(duration: str) -> int:
    if not duration:
        return 0
    h = int((re.search(r'(\d+)H', duration) or [0, 0])[1])
    m = int((re.search(r'(\d+)M', duration) or [0, 0])[1])
    s = int((re.search(r'(\d+)S', duration) or [0, 0])[1])
    return h * 3600 + m * 60 + s


def _is_beauty_related(title: str, description: str) -> bool:
    """タイトル・説明文に美容キーワードが含まれるか"""
    text = (title + " " + description[:200]).lower()
    beauty_words = [
        "beauty", "makeup", "skincare", "skin care", "cosmetic", "lipstick",
        "foundation", "serum", "moisturizer", "sunscreen", "spf", "blush",
        "eyeshadow", "mascara", "hair", "nail", "glow", "routine", "grwm",
        "美容", "スキンケア", "メイク", "コスメ", "化粧", "肌", "美肌",
    ]
    return any(w in text for w in beauty_words)


def _classify_genre(title: str, description: str) -> str:
    text = (title + " " + description[:300]).lower()
    scores: dict[str, int] = {}
    for genre, data in BEAUTY_GENRES.items():
        score = sum(1 for kw in data["keywords"] if kw in text)
        if score > 0:
            scores[genre] = score
    return max(scores, key=lambda g: scores[g]) if scores else "entertainment"


def _fetch_jp_trending_ids() -> set:
    """コスト: 1pt"""
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "id", "chart": "mostPopular", "regionCode": "JP", "maxResults": 50, "key": YOUTUBE_API_KEY},
            timeout=8,
        )
        return {item["id"] for item in resp.json().get("items", [])}
    except Exception:
        return set()


def _fetch_trending(region: str, cat_id: str) -> list:
    """mostPopularで取得。コスト: 1pt/リクエスト"""
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "chart": "mostPopular",
                "regionCode": region,
                "videoCategoryId": cat_id,
                "maxResults": 50,
                "key": YOUTUBE_API_KEY,
            },
            timeout=10,
        )
        return resp.json().get("items", [])
    except Exception:
        return []


def _build_video(item: dict, region: str) -> dict:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    duration_sec = _parse_duration(item.get("contentDetails", {}).get("duration", ""))
    is_short = 0 < duration_sec <= 60
    video_id = item["id"]
    return {
        "id": video_id,
        "platform": "youtube",
        "title": snippet.get("title", ""),
        "thumbnail": (snippet.get("thumbnails", {}).get("high", {}) or {}).get("url", ""),
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "published_at": snippet.get("publishedAt", "")[:10],
        "channel": snippet.get("channelTitle", ""),
        "region": region,
        "is_short": is_short,
        "duration_sec": duration_sec,
        "embed_url": f"https://www.youtube.com/embed/{video_id}",
        "url": f"https://www.youtube.com/shorts/{video_id}" if is_short else f"https://www.youtube.com/watch?v={video_id}",
    }


def fetch_all_videos(jp_ids: set) -> dict[str, dict[str, list]]:
    """海外・日本それぞれの全ジャンルを一括取得してジャンル振り分け（クォータ最小化）"""
    overseas_raw: list[dict] = []
    japan_raw: list[dict] = []

    # 並列でトレンド取得（海外5リージョン×4カテゴリ + JP×4カテゴリ = 最大24リクエスト = 24pt）
    tasks_overseas = [(r, c) for r in OVERSEAS_REGIONS for c in BEAUTY_CATEGORY_IDS]
    tasks_japan = [(JAPAN_REGION, c) for c in BEAUTY_CATEGORY_IDS]

    import threading
    lock = threading.Lock()

    def fetch_overseas(r, c):
        items = _fetch_trending(r, c)
        with lock:
            overseas_raw.extend(items)

    def fetch_japan(r, c):
        items = _fetch_trending(r, c)
        with lock:
            japan_raw.extend(items)

    with ThreadPoolExecutor(max_workers=10) as ex:
        for region, cat_id in tasks_overseas:
            ex.submit(fetch_overseas, region, cat_id)
        for region, cat_id in tasks_japan:
            ex.submit(fetch_japan, region, cat_id)

    def process(items, is_japan):
        result: dict[str, list] = {g: [] for g in BEAUTY_GENRES}
        seen: set[str] = set()
        for item in items:
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            video_id = item.get("id", "")
            if video_id in seen:
                continue
            view_count = int(stats.get("viewCount", 0))
            min_views = 100_000 if is_japan else 1_000_000
            if view_count < min_views:
                continue
            lang = snippet.get("defaultAudioLanguage", "") or snippet.get("defaultLanguage", "")
            if not is_japan and lang.startswith("ja"):
                continue
            if not is_japan and video_id in jp_ids:
                continue
            title = snippet.get("title", "")
            description = snippet.get("description", "")
            # 美容フィルタ削除：全ジャンルのバイラル動画を表示
            genre = _classify_genre(title, description)
            seen.add(video_id)
            region = JAPAN_REGION if is_japan else snippet.get("defaultAudioLanguage", "US")
            v = _build_video(item, region)
            result[genre].append(v)
        for g in result:
            result[g].sort(key=lambda x: x["views"], reverse=True)
        return result

    return {
        "overseas": process(overseas_raw, False),
        "japan": process(japan_raw, True),
    }


def refresh_cache():
    jp_ids = _fetch_jp_trending_ids()
    videos = fetch_all_videos(jp_ids)
    # manualデータを引き継ぐ
    existing = load_cache()
    if "manual" in existing.get("videos", {}):
        videos["manual"] = existing["videos"]["manual"]
    result = {"updated_at": datetime.datetime.now().isoformat(), "videos": videos}
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except (json.JSONDecodeError, Exception):
            pass
    return {"updated_at": None, "videos": {"overseas": {}, "japan": {}}}
