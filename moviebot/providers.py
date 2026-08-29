import os
import logging
import aiohttp

logger = logging.getLogger(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
WATCH_REGION = os.getenv("WATCH_REGION", "GB").upper()

_CACHE = {}


async def tmdb_get(endpoint: str, params=None):
    if not TMDB_API_KEY:
        logger.error("TMDB_API_KEY is missing")
        return None

    params = params or {}
    params["api_key"] = TMDB_API_KEY

    url = f"https://api.themoviedb.org/3/{endpoint}"

    try:
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                url,
                params=params
            ) as response:

                if response.status != 200:
                    logger.warning(
                        "TMDB HTTP %s",
                        response.status
                    )
                    return None

                return await response.json()

    except Exception:
        logger.exception("TMDB request failed")
        return None


async def search_movies(
    query: str,
    language: str = "fa-IR",
):
    data = await tmdb_get(
        "search/movie",
        {
            "query": query,
            "language": language,
            "include_adult": "false",
        },
    )

    if not data:
        return []

    return data.get("results", [])[:10]


async def get_watch_providers(
    movie_id: int,
):
    cache_key = f"{movie_id}:{WATCH_REGION}"

    if cache_key in _CACHE:
        return _CACHE[cache_key]

    data = await tmdb_get(
        f"movie/{movie_id}/watch/providers"
    )

    if not data:
        return None

    result = data.get(
        "results",
        {}
    ).get(WATCH_REGION)

    _CACHE[cache_key] = result

    return result


def movie_text(movie):
    title = (
        movie.get("title")
        or movie.get("original_title")
        or "Unknown"
    )

    original = movie.get(
        "original_title"
    )

    date = movie.get(
        "release_date",
        ""
    )

    year = date[:4] if date else "—"

    rating = movie.get(
        "vote_average",
        0
    )

    overview = (
        movie.get("overview")
        or "توضیحی برای این فیلم ثبت نشده است."
    )

    return (
        f"🎬 <b>{title}</b>\n"
        f"📅 {year}\n"
        f"⭐ امتیاز TMDb: "
        f"{float(rating):.1f}/10\n\n"
        f"📝 {overview}"
    )


def providers_text(
    providers,
):
    if not providers:
        return (
            "🆓 <b>سرویس رایگان</b>\n\n"
            "برای این فیلم سرویس رایگان "
            "گزارش نشده است."
        )

    lines = []

    free = providers.get(
        "free",
        []
    )

    ads = providers.get(
        "ads",
        []
    )

    if free:

        lines.append(
            "🆓 <b>رایگان</b>"
        )

        for item in free:
            lines.append(
                f"• {item.get('provider_name')}"
            )

        lines.append("")

    if ads:

        lines.append(
            "📺 <b>رایگان با تبلیغ</b>"
        )

        for item in ads:
            lines.append(
                f"• {item.get('provider_name')}"
            )

        lines.append("")

    if not lines:

        lines.append(
            "ℹ️ سرویس رایگان "
            "برای این فیلم پیدا نشد."
        )

    return "\n".join(lines)
