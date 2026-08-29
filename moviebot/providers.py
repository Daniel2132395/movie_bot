# providers.py
# ============================================================
# MovieBot - Legal Watch Providers
# aiogram 3.x + TMDb
# ============================================================

import asyncio
import logging
import os
from html import escape
from typing import Optional

import aiohttp
from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

logger = logging.getLogger("MovieBot.providers")

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    "",
).strip()

TMDB_BASE_URL = "https://api.themoviedb.org/3"

DEFAULT_REGION = os.getenv(
    "WATCH_REGION",
    "IR",
).strip().upper()


# ============================================================
# HTTP
# ============================================================

async def _tmdb_get(
    endpoint: str,
    params: Optional[dict] = None,
):
    """
    درخواست GET به TMDb.

    خروجی:
        dict | None
    """

    if not TMDB_API_KEY:
        logger.warning(
            "TMDB_API_KEY is not configured."
        )
        return None

    request_params = {
        "api_key": TMDB_API_KEY,
    }

    if params:
        request_params.update(params)

    url = TMDB_BASE_URL + endpoint

    timeout = aiohttp.ClientTimeout(
        total=12
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                url,
                params=request_params,
            ) as response:

                if response.status != 200:

                    logger.warning(
                        "TMDb HTTP %s for %s",
                        response.status,
                        endpoint,
                    )

                    return None

                return await response.json()

    except asyncio.TimeoutError:

        logger.warning(
            "TMDb request timed out: %s",
            endpoint,
        )

        return None

    except aiohttp.ClientError:

        logger.exception(
            "TMDb network error: %s",
            endpoint,
        )

        return None

    except Exception:

        logger.exception(
            "Unexpected TMDb error: %s",
            endpoint,
        )

        return None


# ============================================================
# SEARCH
# ============================================================

async def search_movies(
    query: str,
    language: str = "fa-IR",
    limit: int = 10,
):
    """
    جستجوی خودکار فیلم و سریال.

    ابتدا فیلم‌ها و سپس سریال‌ها از TMDb گرفته می‌شوند.
    """

    query = (query or "").strip()

    if not query:
        return []

    limit = max(
        1,
        min(int(limit), 20),
    )

    # --------------------------------------------------------
    # Movie
    # --------------------------------------------------------

    movie_data = await _tmdb_get(
        "/search/movie",
        {
            "query": query,
            "language": language,
            "include_adult": "false",
            "page": 1,
        },
    )

    movie_results = (
        movie_data.get("results", [])
        if movie_data
        else []
    )

    # --------------------------------------------------------
    # TV
    # --------------------------------------------------------

    tv_data = await _tmdb_get(
        "/search/tv",
        {
            "query": query,
            "language": language,
            "page": 1,
        },
    )

    tv_results = (
        tv_data.get("results", [])
        if tv_data
        else []
    )

    results = []

    # --------------------------------------------------------
    # Normalize movies
    # --------------------------------------------------------

    for item in movie_results:

        item = dict(item)

        item["_media_type"] = "movie"

        item["title"] = (
            item.get("title")
            or item.get("original_title")
            or "بدون نام"
        )

        item["original_title"] = (
            item.get("original_title")
            or item.get("title")
        )

        results.append(item)

    # --------------------------------------------------------
    # Normalize TV
    # --------------------------------------------------------

    for item in tv_results:

        item = dict(item)

        item["_media_type"] = "tv"

        item["title"] = (
            item.get("name")
            or item.get("original_name")
            or "بدون نام"
        )

        item["original_title"] = (
            item.get("original_name")
            or item.get("name")
        )

        item["release_date"] = (
            item.get("first_air_date")
            or ""
        )

        results.append(item)

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    def sort_key(item):

        try:
            popularity = float(
                item.get(
                    "popularity",
                    0,
                )
                or 0
            )
        except (
            ValueError,
            TypeError,
        ):
            popularity = 0

        try:
            rating = float(
                item.get(
                    "vote_average",
                    0,
                )
                or 0
            )
        except (
            ValueError,
            TypeError,
        ):
            rating = 0

        return (
            popularity,
            rating,
        )

    results.sort(
        key=sort_key,
        reverse=True,
    )

    return results[:limit]


# ============================================================
# MOVIE / TV DETAILS
# ============================================================

async def get_movie_details(
    tmdb_id: int,
    media_type: str = "movie",
    language: str = "fa-IR",
):
    """
    دریافت جزئیات یک فیلم یا سریال.
    """

    if not tmdb_id:
        return None

    if media_type not in (
        "movie",
        "tv",
    ):
        media_type = "movie"

    data = await _tmdb_get(
        f"/{media_type}/{tmdb_id}",
        {
            "language": language,
        },
    )

    if not data:
        return None

    data["_media_type"] = media_type

    if media_type == "tv":

        data["title"] = (
            data.get("name")
            or data.get("original_name")
            or "بدون نام"
        )

        data["original_title"] = (
            data.get("original_name")
            or data.get("name")
        )

        data["release_date"] = (
            data.get("first_air_date")
            or ""
        )

    else:

        data["title"] = (
            data.get("title")
            or data.get("original_title")
            or "بدون نام"
        )

    return data


# ============================================================
# WATCH PROVIDERS
# ============================================================

async def get_watch_providers(
    tmdb_id: int,
    media_type: str = "movie",
    region: Optional[str] = None,
):
    """
    دریافت سرویس‌های قانونی تماشا از TMDb.

    دسته‌ها:

        free
        ads
        flatrate
        rent
        buy

    هیچ URL ساختگی ایجاد نمی‌شود.
    """

    if not tmdb_id:
        return None

    if media_type not in (
        "movie",
        "tv",
    ):
        media_type = "movie"

    region = (
        region
        or DEFAULT_REGION
    ).strip().upper()

    if len(region) != 2:
        region = DEFAULT_REGION

    data = await _tmdb_get(
        f"/{media_type}/{tmdb_id}/watch/providers"
    )

    if not data:
        return None

    countries = data.get(
        "results",
        {},
    )

    country = countries.get(
        region
    )

    # --------------------------------------------------------
    # No legal provider in requested region
    # --------------------------------------------------------

    if not country:

        return {
            "region": region,
            "link": None,
            "free": [],
            "ads": [],
            "flatrate": [],
            "rent": [],
            "buy": [],
            "has_free": False,
            "has_paid": False,
            "has_any": False,
        }

    free = country.get(
        "free",
        []
    ) or []

    ads = country.get(
        "ads",
        []
    ) or []

    flatrate = country.get(
        "flatrate",
        []
    ) or []

    rent = country.get(
        "rent",
        []
    ) or []

    buy = country.get(
        "buy",
        []
    ) or []

    return {
        "region": region,

        # فقط لینک رسمی‌ای که TMDb ارائه می‌کند
        "link": country.get(
            "link"
        ),

        "free": free,
        "ads": ads,
        "flatrate": flatrate,
        "rent": rent,
        "buy": buy,

        "has_free": bool(
            free or ads
        ),

        "has_paid": bool(
            flatrate
            or rent
            or buy
        ),

        "has_any": bool(
            free
            or ads
            or flatrate
            or rent
            or buy
        ),
    }


# ============================================================
# PROVIDER HELPERS
# ============================================================

def provider_name(
    provider: dict,
) -> str:

    return (
        provider.get(
            "provider_name"
        )
        or "Unknown service"
    )


def provider_id(
    provider: dict,
):
    return provider.get(
        "provider_id"
    )


def provider_icon(
    provider: dict,
) -> str:

    name = provider_name(
        provider
    ).lower().strip()

    icons = {
        "netflix": "🔴",
        "amazon prime video": "🔵",
        "prime video": "🔵",
        "apple tv": "",
        "apple tv+": "",
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
        "plex": "🟠",
        "tubi": "📺",
        "pluto tv": "📺",
    }

    return icons.get(
        name,
        "📺",
    )


def provider_button_data(
    provider: dict,
):
    """
    اطلاعات امن برای ساخت دکمه.

    این تابع URL جعلی تولید نمی‌کند.
    """

    name = provider_name(
        provider
    )

    logo_path = provider.get(
        "logo_path"
    )

    return {
        "name": name,
        "icon": provider_icon(
            provider
        ),
        "logo_path": logo_path,
        "provider_id": provider_id(
            provider
        ),
    }


# ============================================================
# DEDUPLICATION
# ============================================================

def _unique_providers(
    providers,
):
    """
    حذف سرویس‌های تکراری.
    """

    result = []

    seen = set()

    for provider in providers or []:

        name = provider_name(
            provider
        ).strip()

        key = name.lower()

        if not name:
            continue

        if key in seen:
            continue

        seen.add(key)

        result.append(
            provider
        )

    return result


# ============================================================
# FORMAT PROVIDERS
# ============================================================

def _format_provider_list(
    providers,
):
    """
    ساخت لیست تمیز سرویس‌ها.
    """

    providers = _unique_providers(
        providers
    )

    lines = []

    for provider in providers:

        data = provider_button_data(
            provider
        )

        lines.append(
            f"{data['icon']} "
            f"<b>{escape(data['name'])}</b>"
        )

    return "\n".join(
        lines
    )


# ============================================================
# PROVIDERS TEXT
# ============================================================

def providers_text(
    providers: Optional[dict],
):
    """
    خروجی تمیز و اولویت‌بندی‌شده.

    ترتیب:

    1. رایگان
    2. رایگان با تبلیغ
    3. اشتراک
    4. اجاره
    5. خرید
    """

    if not providers:

        return (
            "📺 <b>تماشای قانونی</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "😕 اطلاعات سرویس‌های تماشا "
            "در دسترس نیست."
        )

    region = escape(
        providers.get(
            "region",
            DEFAULT_REGION,
        )
    )

    sections = []

    # --------------------------------------------------------
    # FREE
    # --------------------------------------------------------

    free_text = _format_provider_list(
        providers.get(
            "free",
            [],
        )
    )

    if free_text:

        sections.append(
            (
                "🆓 <b>رایگان</b>\n"
                f"{free_text}"
            )
        )

    # --------------------------------------------------------
    # FREE WITH ADS
    # --------------------------------------------------------

    ads_text = _format_provider_list(
        providers.get(
            "ads",
            [],
        )
    )

    if ads_text:

        sections.append(
            (
                "📢 <b>رایگان با تبلیغات</b>\n"
                f"{ads_text}"
            )
        )

    # --------------------------------------------------------
    # SUBSCRIPTION
    # --------------------------------------------------------

    flat_text = _format_provider_list(
        providers.get(
            "flatrate",
            [],
        )
    )

    if flat_text:

        sections.append(
            (
                "💳 <b>اشتراکی</b>\n"
                f"{flat_text}"
            )
        )

    # --------------------------------------------------------
    # RENT
    # --------------------------------------------------------

    rent_text = _format_provider_list(
        providers.get(
            "rent",
            [],
        )
    )

    if rent_text:

        sections.append(
            (
                "🎟 <b>اجاره</b>\n"
                f"{rent_text}"
            )
        )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    buy_text = _format_provider_list(
        providers.get(
            "buy",
            [],
        )
    )

    if buy_text:

        sections.append(
            (
                "🛒 <b>خرید</b>\n"
                f"{buy_text}"
            )
        )

    # --------------------------------------------------------
    # Nothing
    # --------------------------------------------------------

    if not sections:

        return (
            "📺 <b>تماشای قانونی</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"🌍 منطقه: <b>{region}</b>\n\n"
            "🆓 <b>رایگان قانونی:</b>\n"
            "❌ در حال حاضر پیدا نشد.\n\n"
            "ℹ️ سرویس قانونی ثبت‌شده‌ای "
            "برای این منطقه در TMDb وجود ندارد."
        )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    result = (
        "📺 <b>گزینه‌های تماشای قانونی</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"🌍 منطقه: <b>{region}</b>\n\n"
    )

    result += "\n\n".join(
        sections
    )

    # --------------------------------------------------------
    # Official destination
    # --------------------------------------------------------

    if providers.get("link"):

        result += (
            "\n\n"
            "🔗 <b>صفحه رسمی گزینه‌های تماشا</b>"
        )

    return result


# ============================================================
# SIMPLE STATUS
# ============================================================

def watch_status(
    providers: Optional[dict],
):
    """
    وضعیت ساده برای استفاده در bot.py.

    خروجی:
        free
        paid
        free_and_paid
        unavailable
    """

    if not providers:
        return "unavailable"

    has_free = bool(
        providers.get("free")
        or providers.get("ads")
    )

    has_paid = bool(
        providers.get("flatrate")
        or providers.get("rent")
        or providers.get("buy")
    )

    if has_free and has_paid:
        return "free_and_paid"

    if has_free:
        return "free"

    if has_paid:
        return "paid"

    return "unavailable"


# ============================================================
# MOVIE TEXT
# ============================================================

def movie_text(
    movie: dict,
):
    """
    ساخت کارت تمیز فیلم / سریال.
    """

    title = (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "بدون نام"
    )

    original_title = (
        movie.get(
            "original_title"
        )
        or movie.get(
            "original_name"
        )
    )

    date = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    year = (
        date[:4]
        if date
        else "—"
    )

    media_type = movie.get(
        "_media_type",
        "movie",
    )

    if media_type == "tv":
        type_text = "سریال"
        type_icon = "📺"
    else:
        type_text = "فیلم"
        type_icon = "🎬"

    rating = movie.get(
        "vote_average"
    )

    try:

        rating_text = (
            f"{float(rating):.1f}/10"
        )

    except (
        ValueError,
        TypeError,
    ):

        rating_text = "—"

    overview = (
        movie.get("overview")
        or "توضیحی برای این عنوان ثبت نشده است."
    )

    overview = str(
        overview
    ).strip()

    if len(overview) > 500:

        overview = (
            overview[:497]
            + "..."
        )

    title_safe = escape(
        str(title)
    )

    original_safe = (
        escape(
            str(original_title)
        )
        if original_title
        and str(original_title).strip()
        and str(original_title).strip()
        != str(title).strip()
        else None
    )

    overview_safe = escape(
        overview
    )

    lines = [
        f"{type_icon} <b>{title_safe}</b>",
        "━━━━━━━━━━━━━━━━",
        "",
        f"📅 سال: <b>{year}</b>",
        f"⭐ امتیاز TMDb: <b>{rating_text}</b>",
    ]

    if original_safe:

        lines.extend(
            [
                f"🌐 نام اصلی: <b>{original_safe}</b>",
            ]
        )

    lines.extend(
        [
            "",
            f"📝 {overview_safe}",
            "",
            "━━━━━━━━━━━━━━━━",
        ]
    )

    return "\n".join(
        lines
    )


# ============================================================
# WATCH SUMMARY
# ============================================================

def watch_summary(
    providers: Optional[dict],
):
    """
    یک خلاصه کوتاه برای نمایش روی کارت فیلم.
    """

    status = watch_status(
        providers
    )

    if status == "free":
        return "🆓 تماشای رایگان قانونی موجود است"

    if status == "free_and_paid":
        return "🆓 گزینه رایگان + 💳 گزینه‌های اشتراکی موجود است"

    if status == "paid":
        return "💳 گزینه قانونی پولی موجود است"

    return "ℹ️ گزینه رایگان قانونی پیدا نشد"


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "_tmdb_get",
    "search_movies",
    "get_movie_details",
    "get_watch_providers",
    "provider_name",
    "provider_icon",
    "provider_button_data",
    "providers_text",
    "watch_status",
    "watch_summary",
    "movie_text",
    ]
