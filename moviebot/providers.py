# ============================================================
# MovieBot — Iranian Provider Search
# جستجوی واقعی صفحات سرویس‌ها
# بدون TMDb
# ============================================================

import asyncio
import logging
import re
from html import escape
from typing import Optional
from urllib.parse import quote_plus, urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger("MovieBot.providers")

TIMEOUT = aiohttp.ClientTimeout(
    total=20,
    connect=10,
    sock_read=15,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ============================================================
# PROVIDERS
# ============================================================

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
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value: str) -> str:
    if not value:
        return ""
    value = str(value)
    # Arabic → Persian
    value = value.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    # Digits
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    value = value.translate(table)
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def title_matches(query: str, title: str) -> bool:
    q = normalize_text(query)
    t = normalize_text(title)
    if not q or not t:
        return False
    if q in t:
        return True
    q_words = [x for x in q.split() if len(x) >= 2]
    if not q_words:
        return False
    matched = sum(1 for word in q_words if word in t)
    return matched >= max(1, len(q_words) // 2)


# ============================================================
# HTTP
# ============================================================

async def _get_text(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(
            url,
            headers=HEADERS,
            allow_redirects=True,
        ) as response:
            logger.info("GET %s -> HTTP %s", url, response.status)
            if response.status != 200:
                return None
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            return await response.text(errors="ignore")
    except asyncio.TimeoutError:
        logger.warning("Timeout: %s", url)
        return None
    except Exception:
        logger.exception("Request failed: %s", url)
        return None


# ============================================================
# SEARCH URL
# ============================================================

def provider_search_url(provider_key: str, query: str) -> Optional[str]:
    provider = OFFICIAL_PROVIDERS.get(provider_key)
    if not provider:
        return None
    query = (query or "").strip()
    if not query:
        return None
    encoded = quote_plus(query)
    return provider["search_url"].format(query=encoded)


# ============================================================
# EXTRACT LINKS
# ============================================================

def _is_provider_link(provider: dict, url: str) -> bool:
    if not url:
        return False
    domain = provider["domain"].lower()
    url_lower = url.lower()
    return domain in url_lower and url_lower.startswith("http")


def _extract_links(provider_key: str, query: str, html: str):
    provider = OFFICIAL_PROVIDERS[provider_key]
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()
    query_normalized = normalize_text(query)

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href:
            continue
        url = urljoin(provider["home_url"], href)
        if not _is_provider_link(provider, url):
            continue

        lower_url = url.lower()
        ignored = ("/search", "/login", "/register", "/account", "/privacy", "/terms", "/contact")
        if any(part in lower_url for part in ignored):
            continue

        text = a.get_text(" ", strip=True)
        title = text or a.get("title") or ""
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            continue
        if not title_matches(query_normalized, title):
            continue

        key = url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "title": title[:200],
            "url": url,
            "provider_id": provider_key,
            "provider_name": provider["name"],
        })
        if len(results) >= 10:
            break

    return results


def _extract_jsonld(provider_key: str, query: str, html: str):
    provider = OFFICIAL_PROVIDERS[provider_key]
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string
        if not raw:
            continue

        import json
        try:
            data = json.loads(raw)
        except Exception:
            continue

        objects = []
        if isinstance(data, list):
            objects.extend(data)
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                objects.extend(data["@graph"])
            objects.append(data)

        for item in objects:
            if not isinstance(item, dict):
                continue
            title = item.get("name") or item.get("headline") or ""
            url = item.get("url") or ""
            if not title or not url:
                continue
            url = urljoin(provider["home_url"], url)
            if not _is_provider_link(provider, url):
                continue
            if not title_matches(query, title):
                continue
            results.append({
                "title": str(title)[:200],
                "url": url,
                "provider_id": provider_key,
                "provider_name": provider["name"],
            })

    return results


# ============================================================
# SEARCH ONE PROVIDER
# ============================================================

async def search_provider(session: aiohttp.ClientSession, provider_key: str, query: str):
    search_url = provider_search_url(provider_key, query)
    if not search_url:
        return []

    html = await _get_text(session, search_url)
    if not html:
        return []

    results = []
    results.extend(_extract_jsonld(provider_key, query, html))
    results.extend(_extract_links(provider_key, query, html))

    final = []
    seen = set()
    for item in results:
        url = item["url"].rstrip("/")
        if url in seen:
            continue
        seen.add(url)
        final.append(item)

    return final[:10]


# ============================================================
# SEARCH ALL
# ============================================================

async def search_iranian_sources(query: str):
    query = (query or "").strip()
    if not query:
        return []

    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        tasks = [
            search_provider(session, key, query)
            for key in OFFICIAL_PROVIDERS
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for provider_key, response in zip(OFFICIAL_PROVIDERS.keys(), responses):
        if isinstance(response, Exception):
            logger.error("Provider %s failed: %s", provider_key, response)
            continue
        results.extend(response)

    return results


# ============================================================
# SEARCH MOVIES (Main)
# ============================================================

async def search_movies(query: str, language: str = "fa-IR", limit: int = 10):
    query = (query or "").strip()
    if not query:
        return []

    # First try Iranian providers
    providers = await search_iranian_sources(query)

    results = []
    for index, item in enumerate(providers[:limit], start=1):
        results.append({
            "id": index,
            "title": item.get("title", query),
            "name": item.get("title", query),
            "original_title": item.get("title", query),
            "_media_type": "movie",
            "provider_id": item.get("provider_id"),
            "provider_name": item.get("provider_name"),
            "provider_url": item.get("url"),
            "url": item.get("url"),
            "release_date": "",
            "vote_average": None,
            "overview": f"نتیجهٔ پیدا شده در {item.get('provider_name', 'سرویس')}",
        })

    return results


# ============================================================
# COMPATIBILITY FUNCTIONS
# ============================================================

async def get_provider_results(query: str):
    return await search_iranian_sources(query)


async def get_watch_providers(tmdb_id: int, media_type: str = "movie", region: Optional[str] = None):
    """Compatibility with old code - returns None since we don't use TMDb."""
    return None


# ============================================================
# DISPLAY
# ============================================================

def _badges(item: dict) -> str:
    badges = []
    if item.get("free"):
        badges.append("🆓 رایگان")
    if item.get("paid"):
        badges.append("💳 اشتراکی")
    if item.get("dub"):
        badges.append("🎙 دوبله")
    if item.get("subtitle"):
        badges.append("📝 زیرنویس")
    if not badges:
        return "ℹ️ وضعیت پخش در صفحه رسمی سرویس"
    return " • ".join(badges)


def providers_text(providers) -> str:
    if not providers:
        return "😕 <b>نتیجه‌ای در سرویس‌ها پیدا نشد.</b>\n\nنام فیلم را با املای دیگر یا عنوان انگلیسی هم امتحان کن."

    lines = ["🇮🇷 <b>نتایج پیدا شده</b>", "━━━━━━━━━━━━━━━━"]

    for item in providers:
        name = escape(str(item.get("provider_name", item.get("name", "منبع"))))
        title = escape(str(item.get("title", "بدون عنوان")))
        url = item.get("url", item.get("provider_url", ""))

        lines.append(f"\n🎬 <b>{title}</b>\n   🇮🇷 {name}\n   {_badges(item)}")
        if url:
            lines.append(f"   🔗 {escape(url)}")

    return "\n".join(lines)


def movie_text(movie: dict):
    title = movie.get("original_title") or movie.get("title") or movie.get("name") or "بدون عنوان"
    provider_name = movie.get("provider_name") or movie.get("provider_id") or "سرویس"
    overview = movie.get("overview", "اطلاعات بیشتری ثبت نشده است.")

    title = escape(str(title))
    provider_name = escape(str(provider_name))
    overview = escape(str(overview))

    if len(overview) > 500:
        overview = overview[:497] + "..."

    return f"🎬 <b>{title}</b>\n━━━━━━━━━━━━━━━━\n\n🇮🇷 سرویس: <b>{provider_name}</b>\n\n📝 {overview}"
