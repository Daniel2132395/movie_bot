# providers.py
# ============================================================
# MovieBot — Official Iranian Provider Search
# بدون TMDb برای جستجوی سرویس‌ها
# بدون استخراج فایل ویدئو
# ============================================================

import logging
from html import escape
from typing import Optional
from urllib.parse import quote_plus

import aiohttp

logger = logging.getLogger("MovieBot.providers")

TIMEOUT = aiohttp.ClientTimeout(total=12)

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


def _result(
    key: str,
    query: str,
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
        "home_url": provider["home_url"],

        "status": "official_search",

        "dub": False,
        "subtitle": False,
        "free": False,
        "paid": False,
    }


async def search_iranian_sources(
    query: str,
):
    """
    لینک جستجوی رسمی عنوان در سرویس‌ها را برمی‌گرداند.
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


async def search_movies(
    query: str,
    language: str = "fa-IR",
    limit: int = 10,
):
    """
    جستجو بدون TMDb.

    هر نتیجه یک سرویس رسمی است که کاربر می‌تواند
    عنوان موردنظر را در آن جستجو کند.
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

            # عنوان واقعی جستجو
            "title": query,
            "name": query,
            "original_title": query,

            "_media_type": "provider",

            "provider_id": provider["id"],
            "provider_name": provider["name"],
            "provider_url": provider["url"],
            "provider_home": provider["home_url"],

            "release_date": "",
            "vote_average": None,

            "overview": (
                f"جستجوی «{query}» "
                f"در {provider['name']}"
            ),
        })

    return results[:limit]


async def get_watch_providers(
    tmdb_id: int,
    media_type: str = "movie",
    region: Optional[str] = None,
):
    """
    این تابع برای سازگاری با bot.py قدیمی نگه داشته شده.
    """

    return []


async def get_provider_results(
    query: str,
):
    return await search_iranian_sources(
        query
    )


def _badges(
    item: dict,
) -> str:

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
            "ℹ️ وضعیت محتوا در صفحه رسمی سرویس "
            "بررسی شود."
        )

    return " • ".join(badges)


def providers_text(
    providers,
) -> str:

    if not providers:
        return (
            "😕 <b>سرویسی پیدا نشد.</b>"
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
