# providers.py
# ============================================================
# MovieBot - Legal Watch Providers
# ============================================================

import logging
import os
from typing import Optional

import aiohttp
from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    "",
).strip()

TMDB_BASE_URL = (
    "https://api.themoviedb.org/3"
)

DEFAULT_REGION = os.getenv(
    "WATCH_REGION",
    "GB",
).strip().upper()


logger = logging.getLogger(
    __name__
)


# ============================================================
# HTTP HELPER
# ============================================================

async def _tmdb_get(
    endpoint: str,
    params: Optional[dict] = None,
):
    """
    Send a GET request to TMDb.

    Returns:
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
        request_params.update(
            params
        )

    url = (
        TMDB_BASE_URL
        + endpoint
    )

    try:

        timeout = aiohttp.ClientTimeout(
            total=12
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                url,
                params=request_params,
            ) as response:

                if response.status != 200:

                    logger.warning(
                        "TMDb returned HTTP %s",
                        response.status,
                    )

                    return None

                return await response.json()

    except asyncio.TimeoutError:

        logger.warning(
            "TMDb request timed out."
        )

        return None

    except Exception:

        logger.exception(
            "TMDb request failed."
        )

        return None


# ============================================================
# MOVIE SEARCH
# ============================================================

async def search_movies(
    query: str,
    language: str = "fa-IR",
    limit: int = 10,
):
    """
    Search movies and TV shows automatically.

    Returns a list of TMDb results.
    """

    query = query.strip()

    if not query:
        return []

    # --------------------------------------------------------
    # Search movies
    # --------------------------------------------------------

    movie_data = await _tmdb_get(
        "/search/movie",
        {
            "query": query,
            "language": language,
            "include_adult": "false",
        },
    )

    movie_results = (
        movie_data.get(
            "results",
            [],
        )
        if movie_data
        else []
    )

    # --------------------------------------------------------
    # Search TV
    # --------------------------------------------------------

    tv_data = await _tmdb_get(
        "/search/tv",
        {
            "query": query,
            "language": language,
            "include_adult": "false",
        },
    )

    tv_results = (
        tv_data.get(
            "results",
            [],
        )
        if tv_data
        else []
    )

    # --------------------------------------------------------
    # Normalize results
    # --------------------------------------------------------

    results = []

    for item in movie_results:

        item = dict(item)

        item["_media_type"] = "movie"

        results.append(item)

    for item in tv_results:

        item = dict(item)

        item["_media_type"] = "tv"

        # Convert TV fields to movie-like fields
        item["title"] = (
            item.get("name")
            or item.get(
                "original_name"
            )
        )

        item["original_title"] = (
            item.get(
                "original_name"
            )
        )

        item["release_date"] = (
            item.get(
                "first_air_date"
            )
        )

        results.append(item)

    # --------------------------------------------------------
    # Sort by popularity
    # --------------------------------------------------------

    results.sort(
        key=lambda item: (
            float(
                item.get(
                    "popularity",
                    0,
                )
            ),
            float(
                item.get(
                    "vote_average",
                    0,
                )
            ),
        ),
        reverse=True,
    )

    return results[:limit]


# ============================================================
# GET WATCH PROVIDERS
# ============================================================

async def get_watch_providers(
    tmdb_id: int,
    media_type: str = "movie",
    region: Optional[str] = None,
):
    """
    Get legal watch providers from TMDb.

    media_type:
        movie
        tv

    region:
        ISO 3166-1 country code.
        Example:
            GB
            US
            CA
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
    ).upper()

    data = await _tmdb_get(
        f"/{media_type}/{tmdb_id}/watch/providers",
    )

    if not data:
        return None

    results = data.get(
        "results",
        {},
    )

    country = results.get(
        region
    )

    if not country:

        return None

    return {
        "region": region,

        "link": country.get(
            "link"
        ),

        "flatrate": country.get(
            "flatrate",
            [],
        ),

        "free": country.get(
            "free",
            [],
        ),

        "ads": country.get(
            "ads",
            [],
        ),

        "rent": country.get(
            "rent",
            [],
        ),

        "buy": country.get(
            "buy",
            [],
        ),
    }


# ============================================================
# PROVIDER NAME
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


# ============================================================
# PROVIDER ICON
# ============================================================

def provider_icon(
    provider: dict,
) -> str:

    name = provider_name(
        provider
    ).lower()

    icons = {

        "netflix": "🔴",

        "amazon prime video": "🔵",

        "prime video": "🔵",

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

    return icons.get(
        name,
        "📺",
    )


# ============================================================
# PROVIDER LIST
# ============================================================

def _format_provider_list(
    providers,
    title: str,
):
    if not providers:
        return ""

    lines = [
        title
    ]

    seen = set()

    for provider in providers:

        name = provider_name(
            provider
        )

        if name in seen:
            continue

        seen.add(name)

        icon = provider_icon(
            provider
        )

        lines.append(
            f"{icon} {name}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# TEXT OUTPUT
# ============================================================

def providers_text(
    providers: dict,
):
    """
    Convert provider data into
    a clean Telegram message.

    No fake URLs are generated.
    """

    if not providers:
        return (
            "😕 برای این عنوان در منطقه انتخاب‌شده "
            "سرویس تماشای قانونی پیدا نشد."
        )

    region = providers.get(
        "region",
        DEFAULT_REGION,
    )

    sections = []

    flatrate = _format_provider_list(
        providers.get(
            "flatrate",
            [],
        ),
        "📺 <b>تماشا با اشتراک</b>",
    )

    if flatrate:
        sections.append(
            flatrate
        )

    free = _format_provider_list(
        providers.get(
            "free",
            [],
        ),
        "🆓 <b>رایگان</b>",
    )

    if free:
        sections.append(
            free
        )

    ads = _format_provider_list(
        providers.get(
            "ads",
            [],
        ),
        "📢 <b>رایگان با تبلیغات</b>",
    )

    if ads:
        sections.append(
            ads
        )

    rent = _format_provider_list(
        providers.get(
            "rent",
            [],
        ),
        "💳 <b>اجاره</b>",
    )

    if rent:
        sections.append(
            rent
        )

    buy = _format_provider_list(
        providers.get(
            "buy",
            [],
        ),
        "🛒 <b>خرید</b>",
    )

    if buy:
        sections.append(
            buy
        )

    if not sections:

        return (
            f"🌍 منطقه: <b>{region}</b>\n\n"
            "😕 سرویس تماشای قانونی ثبت‌شده‌ای "
            "برای این عنوان پیدا نشد."
        )

    result = (
        f"🌍 منطقه: <b>{region}</b>\n\n"
        + "\n\n".join(
            sections
        )
    )

    link = providers.get(
        "link"
    )

    if link:
        result += (
            "\n\n🔗 <b>صفحه رسمی گزینه‌های تماشا</b>"
        )

    return result


# ============================================================
# MOVIE TEXT
# ============================================================

def movie_text(
    movie: dict,
):
    """
    Create a clean movie card.
    """

    title = (
        movie.get("title")
        or movie.get(
            "name"
        )
        or movie.get(
            "original_title"
        )
        or "Unknown"
    )

    date = (
        movie.get(
            "release_date"
        )
        or movie.get(
            "first_air_date"
        )
        or ""
    )

    year = (
        date[:4]
        if date
        else "—"
    )

    rating = movie.get(
        "vote_average"
    )

    if rating is None:
        rating_text = "—"
    else:
        try:
            rating_text = (
                f"{float(rating):.1f}/10"
            )
        except (
            ValueError,
            TypeError,
        ):
            rating_text = "—"

    media_type = movie.get(
        "_media_type",
        "movie",
    )

    if media_type == "tv":
        type_text = "سریال"
    else:
        type_text = "فیلم"

    overview = (
        movie.get(
            "overview"
        )
        or "توضیحی ثبت نشده است."
    )

    if len(overview) > 450:

        overview = (
            overview[:447]
            + "..."
        )

    return (
        f"🎬 <b>{title}</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"📅 {year}\n"
        f"🎞 نوع: {type_text}\n"
        f"⭐ امتیاز TMDb: {rating_text}\n\n"
        f"📝 {overview}\n\n"
        "━━━━━━━━━━━━━━━━"
    )


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "search_movies",
    "get_watch_providers",
    "movie_text",
    "providers_text",
    ]
