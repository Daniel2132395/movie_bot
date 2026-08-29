# providers.py
# ============================================================
# MovieBot — Iranian Legal Providers
# بدون TMDb برای جستجوی فیلم
# بدون استخراج لینک مستقیم ویدئو
# فقط لینک صفحه/جستجوی سرویس
# ============================================================

import logging
from html import escape
from typing import Optional
from urllib.parse import quote_plus

import aiohttp

logger = logging.getLogger("MovieBot.providers")

TIMEOUT = aiohttp.ClientTimeout(total=12)

# فقط سرویس‌هایی که قرار است به‌عنوان منبع رسمی استفاده شوند.
# این کد فایل ویدئو، mp4، m3u8 یا mpd استخراج نمی‌کند.
OFFICIAL_PROVIDERS = {
    "filimo": {
        "name": "فیلیمو",
        "domain": "filimo.com",
        "search_url": "https://www.filimo.com/search?q={query}",
        "home_url": "https://www.filimo.com/",
    },
    "namava": {
        "name": "نماوا",
        "domain": "namava.ir",
        "search_url": "https://www.namava.ir/search?search={query}",
        "home_url": "https://www.namava.ir/",
    },
    "filmnet": {
        "name": "فیلم‌نت",
        "domain": "filmnet.ir",
        "search_url": "https://filmnet.ir/search/{query}",
        "home_url": "https://filmnet.ir/",
    },
    "tamasha": {
        "name": "تماشا",
        "domain": "tamasha.com",
        "search_url": "https://www.tamasha.com/search?term={query}",
        "home_url": "https://www.tamasha.com/",
    },
    "aparat": {
        "name": "آپارات",
        "domain": "aparat.com",
        "search_url": "https://www.aparat.com/result/{query}",
        "home_url": "https://www.aparat.com/",
    },
}


# ============================================================
# HTTP
# ============================================================

async def _get_text(url: str) -> Optional[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; MovieBot/1.0)"
        )
    }

    try:
        async with aiohttp.ClientSession(
            timeout=TIMEOUT,
            headers=headers,
        ) as session:

            async with session.get(
                url,
                allow_redirects=True,
            ) as response:

                if response.status != 200:
                    logger.info(
                        "Provider returned HTTP %s: %s",
                        response.status,
                        url,
                    )
                    return None

                return await response.text()

    except Exception:
        logger.exception(
            "Provider request failed: %s",
            url,
        )
        return None


# ============================================================
# SEARCH URL
# ============================================================

def provider_search_url(
    provider_key: str,
    query: str,
) -> Optional[str]:

    provider = OFFICIAL_PROVIDERS.get(provider_key)

    if not provider:
        return None

    query = (query or "").strip()

    if not query:
        return None

    encoded = quote_plus(query)

    return provider["search_url"].format(
        query=encoded
    )


# ============================================================
# RESULT
# ============================================================

def _result(
    key: str,
    query: str,
    *,
    status: str = "search",
):
    provider = OFFICIAL_PROVIDERS[key]

    return {
        "id": key,
        "name": provider["name"],
        "domain": provider["domain"],
        "url": provider_search_url(
            key,
            query,
        ),
        "status": status,

        # عمداً اطلاعات ساختگی زبان/هزینه نمی‌سازیم.
        "dub": False,
        "subtitle": False,
        "free": False,
        "paid": False,
    }


# ============================================================
# IRANIAN PROVIDERS SEARCH
# ============================================================

async def search_iranian_sources(
    query: str,
):
    """
    فقط لینک جستجوی رسمی سرویس‌ها را تولید می‌کند.

    هیچ فایل ویدئویی استخراج نمی‌شود.
    """

    query = (query or "").strip()

    if not query:
        return []

    results = []

    for key in OFFICIAL_PROVIDERS:

        item = _result(
            key,
            query,
        )

        if item.get("url"):
            results.append(item)

    return results


# ============================================================
# MOVIE SEARCH
# ============================================================

async def search_movies(
    query: str,
    language: str = "fa-IR",
    limit: int = 10,
):
    """
    جستجوی فیلم بدون TMDb.

    خروجی به‌صورت نتیجه‌های سرویس‌های ایرانی است.
    چون بعضی سرویس‌ها جستجوی خود را با JavaScript
    اجرا می‌کنند، به جای جعل نتیجه، لینک جستجوی
    رسمی همان سرویس را برمی‌گردانیم.
    """

    query = (query or "").strip()

    if not query:
        return []

    providers = await search_iranian_sources(
        query
    )

    results = []

    for provider in providers[:limit]:

        results.append({
            "id": provider["id"],
            "title": provider["name"],
            "name": provider["name"],
            "original_title": query,

            # برای سازگاری با bot.py
            "_media_type": "movie",

            "provider_id": provider["id"],
            "provider_name": provider["name"],
            "provider_url": provider["url"],

            "release_date": "",
            "vote_average": None,

            "overview": (
                f"برای «{query}» "
                f"در {provider['name']} جستجو کن."
            ),
        })

    return results[:limit]


# ============================================================
# PROVIDERS
# ============================================================

async def get_watch_providers(
    tmdb_id: int,
    media_type: str = "movie",
    region: Optional[str] = None,
):
    """
    سازگاری با bot.py قدیمی.

    TMDb استفاده نمی‌شود.

    چون این تابع شناسه TMDb دریافت می‌کند، نمی‌تواند
    عنوان واقعی را از TMDb بگیرد. بنابراین bot.py جدید
    باید از provider نتایج جستجو استفاده کند.
    """

    return None


# ============================================================
# PROVIDER SEARCH FOR SELECTED RESULT
# ============================================================

async def get_provider_results(
    query: str,
):
    """
    جستجوی مستقیم یک عنوان در تمام سرویس‌های تعریف‌شده.
    """

    return await search_iranian_sources(
        query
    )


# ============================================================
# DISPLAY
# ============================================================

def _badges(item: dict) -> str:

    badges = []

    if item.get("free"):
        badges.append("🆓 رایگان")

    if item.get("paid"):
        badges.append("💳 اشتراکی/خرید")

    if item.get("dub"):
        badges.append("🎙 دوبله")

    if item.get("subtitle"):
        badges.append("📝 زیرنویس")

    if not badges:
        return (
            "ℹ️ وضعیت دوبله، زیرنویس و هزینه "
            "در صفحه رسمی سرویس بررسی شود"
        )

    return " • ".join(badges)


def providers_text(
    providers,
) -> str:

    if not providers:
        return (
            "😕 <b>منبع قانونی پیدا نشد.</b>"
        )

    lines = [
        "🇮🇷 <b>سرویس‌های رسمی</b>",
        "━━━━━━━━━━━━━━━━",
    ]

    for item in providers:

        name = escape(
            str(
                item.get(
                    "name",
                    "منبع",
                )
            )
        )

        url = item.get("url") or ""

        lines.append(
            f"\n🎬 <b>{name}</b>\n"
            f"   {_badges(item)}\n"
            f"   🔗 {escape(url)}"
        )

    return "\n".join(lines)


# ============================================================
# MOVIE TEXT
# ============================================================

def movie_text(
    movie: dict,
):

    title = (
        movie.get("original_title")
        or movie.get("title")
        or movie.get("name")
        or "بدون عنوان"
    )

    title = escape(
        str(title)
    )

    provider_name = escape(
        str(
            movie.get(
                "provider_name",
                "",
            )
        )
    )

    overview = escape(
        str(
            movie.get(
                "overview",
                "توضیحی ثبت نشده است.",
            )
        )
    )

    if len(overview) > 500:
        overview = overview[:497] + "..."

    return (
        f"🎬 <b>{title}</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"🇮🇷 سرویس: <b>{provider_name}</b>\n\n"
        f"📝 {overview}"
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "search_iranian_sources",
    "search_movies",
    "get_watch_providers",
    "get_provider_results",
    "provider_search_url",
    "providers_text",
    "movie_text",
    "OFFICIAL_PROVIDERS",
]
