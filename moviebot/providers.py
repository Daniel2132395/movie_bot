# providers.py
# ============================================================
# MovieBot — Iranian Legal Providers
# فقط منابع ایرانیِ عمومی و قانونی
# بدون TMDb Watch Providers و بدون اسکن سایت‌های ناشناس
# ============================================================

import logging
import os
from html import escape
from typing import Optional
from urllib.parse import quote_plus

import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("MovieBot.providers")

TIMEOUT = aiohttp.ClientTimeout(total=12)

# فقط دامنه‌هایی که خودشان سرویس/صفحه عمومی ارائه می‌کنند.
# لینک مستقیم فایل ویدئو ساخته نمی‌شود.
OFFICIAL_PROVIDERS = {
    "filimo": {
        "name": "فیلیمو",
        "domain": "filimo.com",
        "search_url": "https://www.filimo.com/search?q={query}",
    },
    "namava": {
        "name": "نماوا",
        "domain": "namava.ir",
        "search_url": "https://www.namava.ir/search?search={query}",
    },
    "aparat": {
        "name": "آپارات",
        "domain": "aparat.com",
        "search_url": "https://www.aparat.com/result/{query}",
    },
    "filmnet": {
        "name": "فیلم‌نت",
        "domain": "filmnet.ir",
        "search_url": "https://filmnet.ir/search/{query}",
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
# SEARCH URLS
# ============================================================

def provider_search_url(
    provider_key: str,
    query: str,
) -> Optional[str]:

    provider = OFFICIAL_PROVIDERS.get(
        provider_key
    )

    if not provider:
        return None

    encoded = quote_plus(
        query.strip()
    )

    return provider["search_url"].format(
        query=encoded
    )


# ============================================================
# PROVIDER RESULT
# ============================================================

def _result(
    key: str,
    query: str,
    *,
    status: str = "search",
    dub: bool = False,
    subtitle: bool = False,
    free: bool = False,
    paid: bool = False,
):
    provider = OFFICIAL_PROVIDERS[key]

    return {
        "id": key,
        "name": provider["name"],
        "url": provider_search_url(
            key,
            query,
        ),
        "status": status,
        "dub": dub,
        "subtitle": subtitle,
        "free": free,
        "paid": paid,
    }


# ============================================================
# LEGAL IRANIAN PROVIDERS
# ============================================================

async def search_iranian_sources(
    query: str,
):
    """
    جستجوی منابع ایرانی.

    نکته:
    صرف وجود عنوان در یک سایت به معنی مجازبودن
    انتشار آن نیست؛ بنابراین وضعیت «قانونی»
    از خودمان حدس زده نمی‌شود.

    این تابع لینک صفحه جستجوی عمومی سرویس را
    برمی‌گرداند، نه لینک فایل ویدئو.
    """

    query = (
        query or ""
    ).strip()

    if not query:
        return []

    results = []

    # صفحات رسمی جستجو.
    # دسترسی به محتوا همچنان توسط خود سرویس کنترل می‌شود.

    for key in OFFICIAL_PROVIDERS:

        url = provider_search_url(
            key,
            query,
        )

        if not url:
            continue

        results.append(
            _result(
                key,
                query,
            )
        )

    return results


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

    return (
        " • ".join(badges)
        if badges
        else "ℹ️ اطلاعات زبان/هزینه باید در صفحه رسمی سرویس بررسی شود"
    )


def providers_text(
    providers,
) -> str:

    if not providers:
        return (
            "😕 <b>منبع ایرانی پیدا نشد.</b>"
        )

    lines = [
        "🇮🇷 <b>منابع ایرانی</b>",
        "━━━━━━━━━━━━━━━━",
    ]

    for item in providers:

        name = escape(
            item.get(
                "name",
                "منبع",
            )
        )

        lines.append(
            f"\n🎬 <b>{name}</b>\n"
            f"   {_badges(item)}"
        )

    return "\n".join(lines)


# ============================================================
# MOVIE TEXT
# ============================================================

def movie_text(
    movie: dict,
):

    title = (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or "بدون عنوان"
    )

    title = escape(
        str(title)
    )

    date = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    year = (
        str(date)[:4]
        if date
        else "—"
    )

    rating = movie.get(
        "vote_average"
    )

    try:
        rating_text = (
            f"{float(rating):.1f}/10"
        )
    except (
        TypeError,
        ValueError,
    ):
        rating_text = "—"

    media_type = movie.get(
        "_media_type",
        "movie",
    )

    kind = (
        "سریال"
        if media_type == "tv"
        else "فیلم"
    )

    overview = (
        movie.get("overview")
        or "توضیحی ثبت نشده است."
    )

    overview = escape(
        str(overview)
    )

    if len(overview) > 500:
        overview = (
            overview[:497]
            + "..."
        )

    return (
        f"🎬 <b>{title}</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"📅 سال: <b>{year}</b>\n"
        f"🎞 نوع: <b>{kind}</b>\n"
        f"⭐ امتیاز: <b>{rating_text}</b>\n\n"
        f"📝 {overview}"
    )


# ============================================================
# COMPATIBILITY
# ============================================================

async def search_movies(
    query: str,
    language: str = "fa-IR",
    limit: int = 10,
):
    """
    برای سازگاری با bot.py فعلی.

    جستجوی عنوان فیلم/سریال باید توسط موتور
    اصلی پروژه انجام شود. این تابع فقط یک لیست
    خالی برمی‌گرداند تا providers.py وابستگی
    اجباری به TMDb نداشته باشد.
    """

    return []


async def get_watch_providers(
    tmdb_id: int,
    media_type: str = "movie",
    region: Optional[str] = None,
):
    """
    سازگاری با bot.py قدیمی.

    این نسخه عمداً TMDb Watch Providers را
    استفاده نمی‌کند.
    """

    return None


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "search_iranian_sources",
    "search_movies",
    "get_watch_providers",
    "provider_search_url",
    "providers_text",
    "movie_text",
]
```0
