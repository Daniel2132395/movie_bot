# providers.py
# ============================================================
# MovieBot — Legal Iran Watch Providers
# فقط منابعی که امکان دسترسی قانونی دارند
# ============================================================

import asyncio
import logging
import os
from typing import Optional
from urllib.parse import quote_plus

import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("MovieBot.providers")

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
TMDB_BASE_URL = "https://api.themoviedb.org/3"
DEFAULT_REGION = "IR"


# ============================================================
# TMDb
# ============================================================

async def _tmdb_get(
    endpoint: str,
    params: Optional[dict] = None,
):
    if not TMDB_API_KEY:
        return None

    request_params = {
        "api_key": TMDB_API_KEY,
    }

    if params:
        request_params.update(params)

    try:
        timeout = aiohttp.ClientTimeout(total=12)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                TMDB_BASE_URL + endpoint,
                params=request_params,
            ) as response:

                if response.status != 200:
                    logger.warning(
                        "TMDb HTTP %s: %s",
                        response.status,
                        endpoint,
                    )
                    return None

                return await response.json()

    except asyncio.TimeoutError:
        logger.warning("TMDb timeout")
        return None

    except Exception:
        logger.exception("TMDb request failed")
        return None


# ============================================================
# SEARCH
# ============================================================

async def search_movies(
    query: str,
    language: str = "fa-IR",
    limit: int = 10,
):
    query = (query or "").strip()

    if not query:
        return []

    movie_data = await _tmdb_get(
        "/search/movie",
        {
            "query": query,
            "language": language,
            "region": DEFAULT_REGION,
            "include_adult": "false",
        },
    )

    tv_data = await _tmdb_get(
        "/search/tv",
        {
            "query": query,
            "language": language,
            "include_adult": "false",
        },
    )

    results = []

    for item in (movie_data or {}).get("results", []):
        item = dict(item)
        item["_media_type"] = "movie"
        results.append(item)

    for item in (tv_data or {}).get("results", []):
        item = dict(item)
        item["_media_type"] = "tv"
        item["title"] = (
            item.get("name")
            or item.get("original_name")
        )
        item["original_title"] = item.get("original_name")
        item["release_date"] = item.get("first_air_date")
        results.append(item)

    results.sort(
        key=lambda x: (
            float(x.get("popularity") or 0),
            float(x.get("vote_average") or 0),
        ),
        reverse=True,
    )

    return results[:limit]


# ============================================================
# WATCH PROVIDERS — IR
# ============================================================

async def get_watch_providers(
    tmdb_id: int,
    media_type: str = "movie",
    region: str = "IR",
):
    if not tmdb_id:
        return None

    media_type = (
        "tv"
        if media_type == "tv"
        else "movie"
    )

    # این بخش عمداً فقط IR را بررسی می‌کند.
    region = "IR"

    data = await _tmdb_get(
        f"/{media_type}/{tmdb_id}/watch/providers"
    )

    if not data:
        return None

    country = (
        data.get("results", {})
        .get(region)
    )

    if not country:
        return {
            "region": region,
            "link": None,
            "flatrate": [],
            "free": [],
            "ads": [],
            "rent": [],
            "buy": [],
        }

    return {
        "region": region,
        "link": country.get("link"),
        "flatrate": country.get("flatrate", []),
        "free": country.get("free", []),
        "ads": country.get("ads", []),
        "rent": country.get("rent", []),
        "buy": country.get("buy", []),
    }


# ============================================================
# PROVIDER HELPERS
# ============================================================

def provider_name(provider: dict) -> str:
    return (
        provider.get("provider_name")
        or "Unknown"
    )


def provider_icon(provider: dict) -> str:
    name = provider_name(provider).lower()

    icons = {
        "netflix": "🔴",
        "prime video": "🔵",
        "amazon prime video": "🔵",
        "apple tv": "",
        "disney plus": "🔷",
        "disney+": "🔷",
        "youtube": "▶️",
        "youtube premium": "▶️",
        "max": "🟣",
        "hbo max": "🟣",
        "paramount+": "⭐",
        "hulu": "🟢",
        "peacock": "🦚",
        "crunchyroll": "🟠",
        "mubi": "⚫",
    }

    return icons.get(name, "📺")


def _provider_list(
    providers,
    title: str,
):
    if not providers:
        return ""

    lines = [title]
    seen = set()

    for provider in providers:
        name = provider_name(provider)

        if name in seen:
            continue

        seen.add(name)

        lines.append(
            f"{provider_icon(provider)} {name}"
        )

    return "\n".join(lines)


# ============================================================
# APARAT — SEARCH ONLY
# ============================================================

def aparat_search_url(title: str) -> str:
    """
    لینک جستجوی آپارات.
    این لینک فقط جستجو است و ربات ادعای
    مجاز بودن تک‌تک نتایج را نمی‌کند.
    """
    return (
        "https://www.aparat.com/result/"
        + quote_plus(title)
    )


# ============================================================
# LEGAL IR SOURCES
# ============================================================

IRANIAN_LEGAL_SOURCES = [
    {
        "name": "آپارات",
        "icon": "▶️",
        "url": "https://www.aparat.com/",
        "search": True,
    },
    {
        "name": "فیلیمو",
        "icon": "🎬",
        "url": "https://www.filimo.com/",
        "search": False,
    },
    {
        "name": "نماوا",
        "icon": "📺",
        "url": "https://www.namava.ir/",
        "search": False,
    },
    {
        "name": "فیلم‌نت",
        "icon": "🎞️",
        "url": "https://filmnet.ir/",
        "search": False,
    },
]


def iranian_sources_text(
    title: str,
) -> str:
    lines = [
        "🇮🇷 <b>منابع ایرانی</b>",
        "",
        "منابع رسمی را می‌توانی برای بررسی "
        "دسترسی قانونی این عنوان باز کنی.",
        "",
    ]

    for source in IRANIAN_LEGAL_SOURCES:
        lines.append(
            f"{source['icon']} <b>{source['name']}</b>"
        )

    return "\n".join(lines)


# ============================================================
# CLEAN PROVIDER TEXT
# ============================================================

def providers_text(
    providers: Optional[dict],
):
    if not providers:
        return (
            "📺 <b>گزینه‌های تماشا</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "😕 اطلاعات سرویس تماشا برای این عنوان "
            "در منطقه ایران پیدا نشد."
        )

    sections = []

    flatrate = _provider_list(
        providers.get("flatrate", []),
        "📺 <b>اشتراک</b>",
    )

    free = _provider_list(
        providers.get("free", []),
        "🆓 <b>رایگان</b>",
    )

    ads = _provider_list(
        providers.get("ads", []),
        "📢 <b>رایگان با تبلیغات</b>",
    )

    rent = _provider_list(
        providers.get("rent", []),
        "💳 <b>اجاره</b>",
    )

    buy = _provider_list(
        providers.get("buy", []),
        "🛒 <b>خرید</b>",
    )

    for section in (
        free,
        ads,
        flatrate,
        rent,
        buy,
    ):
        if section:
            sections.append(section)

    if not sections:
        sections.append(
            "😕 سرویس تماشای ثبت‌شده‌ای "
            "برای ایران پیدا نشد."
        )

    return (
        "📺 <b>گزینه‌های تماشا</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "🇮🇷 منطقه: <b>ایران</b>\n\n"
        + "\n\n".join(sections)
    )


# ============================================================
# MOVIE TEXT
# ============================================================

def movie_text(movie: dict):
    title = (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or "بدون نام"
    )

    date = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    year = date[:4] if date else "—"

    rating = movie.get("vote_average")

    try:
        rating_text = f"{float(rating):.1f}/10"
    except (TypeError, ValueError):
        rating_text = "—"

    media_type = movie.get(
        "_media_type",
        "movie",
    )

    type_text = (
        "📺 سریال"
        if media_type == "tv"
        else "🎬 فیلم"
    )

    overview = (
        movie.get("overview")
        or "توضیحی برای این عنوان ثبت نشده است."
    )

    if len(overview) > 450:
        overview = overview[:447] + "..."

    return (
        f"🎬 <b>{title}</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"📅 سال: <b>{year}</b>\n"
        f"🎞 نوع: <b>{type_text}</b>\n"
        f"⭐ امتیاز TMDb: <b>{rating_text}</b>\n\n"
        f"📝 {overview}\n\n"
        "━━━━━━━━━━━━━━━━"
    )


__all__ = [
    "search_movies",
    "get_watch_providers",
    "providers_text",
    "movie_text",
    "aparat_search_url",
    "iranian_sources_text",
    "IRANIAN_LEGAL_SOURCES",
    "_tmdb_get",
]
```0
