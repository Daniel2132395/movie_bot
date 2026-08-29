# providers.py
# ============================================================
# MovieBot Providers
# TMDb search + public Iranian provider search
#
# نکته:
# - از TMDb Watch Providers استفاده نمی‌شود.
# - فقط صفحات عمومی سرویس‌ها بررسی می‌شوند.
# - لینک مستقیم فایل ویدئو ساخته نمی‌شود.
# - robots.txt / sitemap عمومی در صورت وجود بررسی می‌شود.
# - هیچ احراز هویت یا دور زدن محدودیت دسترسی انجام نمی‌شود.
# ============================================================

import asyncio
import json
import logging
import os
import re
from html import escape
from typing import Any, Optional
from urllib.parse import (
    quote_plus,
    urljoin,
    urlparse,
)

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("MovieBot.providers")

# ============================================================
# CONFIG
# ============================================================

TIMEOUT = aiohttp.ClientTimeout(
    total=15,
    connect=8,
    sock_read=12,
)

MAX_PROVIDER_RESULTS = 8
MAX_SITEMAP_URLS = 2500
MAX_SITEMAP_FILES = 8
MAX_HTML_LINKS = 120

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    "",
).strip()

TMDB_BASE_URL = (
    "https://api.themoviedb.org/3"
)

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; MovieBot/2.0; "
    "+https://www.themoviedb.org/)"
)


# ============================================================
# PROVIDERS
# ============================================================

# search_url:
#   صفحه جستجوی عمومی سرویس
#
# sitemap:
#   sitemap عمومی اصلی، در صورت وجود
#
# allowed_hosts:
#   دامنه اصلی + زیردامنه‌های همان دامنه
#
# توجه:
# وجود یک سایت در این لیست به معنی تأیید وضعیت حقوقی
# محتوای تک‌تک صفحات آن نیست.
# ============================================================

OFFICIAL_PROVIDERS = {
    "filimo": {
        "name": "فیلیمو",
        "domain": "filimo.com",
        "search_url": (
            "https://www.filimo.com/search?q={query}"
        ),
        "sitemap": (
            "https://www.filimo.com/sitemap.xml"
        ),
    },

    "namava": {
        "name": "نماوا",
        "domain": "namava.ir",
        "search_url": (
            "https://www.namava.ir/search?search={query}"
        ),
        "sitemap": (
            "https://www.namava.ir/sitemap.xml"
        ),
    },

    "filmnet": {
        "name": "فیلم‌نت",
        "domain": "filmnet.ir",
        "search_url": (
            "https://filmnet.ir/search/{query}"
        ),
        "sitemap": (
            "https://filmnet.ir/sitemap.xml"
        ),
    },

    "tamasha": {
        "name": "تماشا",
        "domain": "tamasha.com",
        "search_url": (
            "https://www.tamasha.com/search?term={query}"
        ),
        "sitemap": (
            "https://www.tamasha.com/sitemap.xml"
        ),
    },

    "aparat": {
        "name": "آپارات",
        "domain": "aparat.com",
        "search_url": (
            "https://www.aparat.com/result/{query}"
        ),
        "sitemap": (
            "https://www.aparat.com/sitemap.xml"
        ),
    },

    # --------------------------------------------------------
    # این سه دامنه در کد قبلی شما بودند.
    # در این نسخه صرفاً به عنوان منابع عمومی درج شده‌اند.
    # وضعیت حقوقی هر عنوان باید از خود سرویس بررسی شود.
    # --------------------------------------------------------

    "movielandz": {
        "name": "مووی‌لندز",
        "domain": "movielandz.com",
        "search_url": (
            "https://movielandz.com/?s={query}"
        ),
        "sitemap": (
            "https://movielandz.com/sitemap.xml"
        ),
    },

    "melofilm": {
        "name": "ملوفیلم",
        "domain": "melofilm.ir",
        "search_url": (
            "https://melofilm.ir/?s={query}"
        ),
        "sitemap": (
            "https://melofilm.ir/sitemap.xml"
        ),
    },

    "zardfilm": {
        "name": "زردفیلم",
        "domain": "zardfilm.in",
        "search_url": (
            "https://zardfilm.in/?s={query}"
        ),
        "sitemap": (
            "https://zardfilm.in/sitemap.xml"
        ),
    },
}


# ============================================================
# HTTP
# ============================================================

async def _get_text(
    url: str,
    *,
    session: Optional[aiohttp.ClientSession] = None,
) -> Optional[str]:

    own_session = session is None

    if own_session:
        session = aiohttp.ClientSession(
            timeout=TIMEOUT,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": (
                    "fa-IR,fa;q=0.9,en;q=0.7"
                ),
            },
        )

    try:
        assert session is not None

        async with session.get(
            url,
            allow_redirects=True,
            max_redirects=5,
        ) as response:

            if response.status != 200:
                logger.info(
                    "HTTP %s: %s",
                    response.status,
                    url,
                )
                return None

            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                ).lower()
            )

            # فقط متن/HTML/XML
            if not any(
                x in content_type
                for x in (
                    "text/",
                    "html",
                    "xml",
                    "json",
                )
            ):
                return None

            return await response.text(
                errors="ignore"
            )

    except (
        asyncio.TimeoutError,
        aiohttp.ClientError,
    ):
        logger.warning(
            "Provider request failed: %s",
            url,
        )
        return None

    except Exception:
        logger.exception(
            "Unexpected provider error: %s",
            url,
        )
        return None

    finally:
        if own_session and session:
            await session.close()


# ============================================================
# URL / DOMAIN HELPERS
# ============================================================

def _normalize_host(host: str) -> str:

    host = (
        host or ""
    ).lower().strip()

    if host.startswith("www."):
        host = host[4:]

    return host


def _is_allowed_host(
    url: str,
    provider: dict,
) -> bool:

    try:
        host = _normalize_host(
            urlparse(url).hostname or ""
        )
    except Exception:
        return False

    domain = _normalize_host(
        provider["domain"]
    )

    if not host:
        return False

    return (
        host == domain
        or host.endswith(
            "." + domain
        )
    )


def _clean_url(
    url: str,
) -> str:

    return (
        url
        .replace("\\/", "/")
        .strip()
    )


# ============================================================
# SEARCH URL
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
        (query or "").strip()
    )

    return provider[
        "search_url"
    ].format(
        query=encoded
    )


# ============================================================
# QUERY VARIANTS
# ============================================================

def _normalize_query(
    value: str,
) -> str:

    value = (
        value or ""
    ).lower().strip()

    # نیم‌فاصله
    value = value.replace(
        "\u200c",
        " ",
    )

    # عربی → فارسی
    value = value.replace(
        "ي",
        "ی",
    )

    value = value.replace(
        "ى",
        "ی",
    )

    value = value.replace(
        "ك",
        "ک",
    )

    # حذف علائم
    value = re.sub(
        r"[^\w\u0600-\u06ff]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def _query_tokens(
    query: str,
) -> list[str]:

    normalized = _normalize_query(
        query
    )

    return [
        token
        for token in normalized.split()
        if len(token) >= 2
    ]


def _query_variants(
    title: str,
    original_title: Optional[str] = None,
    year: Optional[str] = None,
) -> list[str]:

    values = []

    for value in (
        title,
        original_title,
    ):

        if value:
            value = str(value).strip()

            if value:
                values.append(value)

    if year:
        year = str(year).strip()

        # عنوان + سال
        for value in list(values):
            values.append(
                f"{value} {year}"
            )

    result = []
    seen = set()

    for value in values:

        key = _normalize_query(
            value
        )

        if (
            key
            and key not in seen
        ):
            seen.add(key)
            result.append(value)

    return result


# ============================================================
# MATCHING
# ============================================================

def _similarity_score(
    query: str,
    text: str,
) -> int:

    q = _normalize_query(
        query
    )

    t = _normalize_query(
        text
    )

    if not q or not t:
        return 0

    score = 0

    if q == t:
        score += 100

    if q in t:
        score += 70

    q_tokens = _query_tokens(q)

    if q_tokens:

        matched = sum(
            1
            for token in q_tokens
            if token in t
        )

        score += int(
            30
            * matched
            / len(q_tokens)
        )

    return min(
        score,
        100,
    )


def _is_good_match(
    query: str,
    title: str,
) -> bool:

    score = _similarity_score(
        query,
        title,
    )

    return score >= 40


# ============================================================
# HTML PARSING
# ============================================================

def _absolute_links(
    base_url: str,
    html: str,
    provider: dict,
) -> list[str]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    links = []
    seen = set()

    for tag in soup.find_all(
        "a",
        href=True,
    )[:MAX_HTML_LINKS]:

        href = (
            tag.get(
                "href",
                "",
            )
            or ""
        ).strip()

        if not href:
            continue

        if href.startswith(
            (
                "#",
                "javascript:",
                "mailto:",
                "tel:",
            )
        ):
            continue

        url = urljoin(
            base_url,
            href,
        )

        parsed = urlparse(
            url
        )

        if parsed.scheme not in (
            "http",
            "https",
        ):
            continue

        if not _is_allowed_host(
            url,
            provider,
        ):
            continue

        # حذف fragment
        clean = url.split(
            "#",
            1,
        )[0]

        if clean not in seen:
            seen.add(clean)
            links.append(clean)

    return links


def _page_title(
    html: str,
) -> str:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # title
    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True,
        )

        if title:
            return title

    # og:title
    og = soup.find(
        "meta",
        attrs={
            "property": "og:title"
        },
    )

    if og:
        value = og.get(
            "content",
            "",
        )

        if value:
            return value.strip()

    # h1
    h1 = soup.find("h1")

    if h1:
        value = h1.get_text(
            " ",
            strip=True,
        )

        if value:
            return value

    return ""


def _extract_jsonld(
    html: str,
) -> list[dict]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    items = []

    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):

        raw = script.string

        if not raw:
            continue

        try:

            data = json.loads(
                raw
            )

        except Exception:
            continue

        if isinstance(
            data,
            dict,
        ):

            items.append(data)

            graph = data.get(
                "@graph"
            )

            if isinstance(
                graph,
                list,
            ):

                for item in graph:

                    if isinstance(
                        item,
                        dict,
                    ):
                        items.append(
                            item
                        )

        elif isinstance(
            data,
            list,
        ):

            for item in data:

                if isinstance(
                    item,
                    dict,
                ):
                    items.append(
                        item
                    )

    return items


def _extract_movie_info(
    html: str,
) -> dict:

    title = _page_title(
        html
    )

    year = None

    for item in _extract_jsonld(
        html
    ):

        item_type = item.get(
            "@type",
            "",
        )

        if isinstance(
            item_type,
            list,
        ):
            item_type = " ".join(
                map(
                    str,
                    item_type,
                )
            )

        if any(
            x in str(
                item_type
            ).lower()
            for x in (
                "movie",
                "tvseries",
                "creativework",
            )
        ):

            name = item.get(
                "name"
            )

            if name:
                title = str(
                    name
                ).strip()

            date = (
                item.get(
                    "dateCreated"
                )
                or item.get(
                    "datePublished"
                )
                or item.get(
                    "releaseDate"
                )
            )

            if date:
                match = re.search(
                    r"\b(19|20)\d{2}\b",
                    str(date),
                )

                if match:
                    year = match.group(
                        0
                    )

    if not year:

        match = re.search(
            r"\b(19|20)\d{2}\b",
            title,
        )

        if match:
            year = match.group(
                0
            )

    return {
        "title": title.strip(),
        "year": year,
    }


# ============================================================
# ROBOTS.TXT
# ============================================================

async def _get_sitemaps_from_robots(
    provider: dict,
    session: aiohttp.ClientSession,
) -> list[str]:

    robots_url = (
        "https://"
        + provider["domain"]
        + "/robots.txt"
    )

    text = await _get_text(
        robots_url,
        session=session,
    )

    if not text:
        return []

    result = []

    for line in text.splitlines():

        if ":" not in line:
            continue

        key, value = line.split(
            ":",
            1,
        )

        if key.strip().lower() != "sitemap":
            continue

        url = value.strip()

        if (
            url.startswith(
                "http://"
            )
            or url.startswith(
                "https://"
            )
        ):

            if _is_allowed_host(
                url,
                provider,
            ):
                result.append(url)

    return result


# ============================================================
# SITEMAP
# ============================================================

def _parse_sitemap_urls(
    xml: str,
) -> tuple[list[str], list[str]]:

    soup = BeautifulSoup(
        xml,
        "xml",
    )

    urls = []
    sitemaps = []

    for loc in soup.find_all(
        "loc"
    ):

        value = (
            loc.get_text(
                strip=True
            )
        )

        if not value:
            continue

        parent = loc.parent

        if parent and parent.name == "sitemap":
            sitemaps.append(value)
        else:
            urls.append(value)

    return urls, sitemaps


async def _collect_sitemap_urls(
    provider: dict,
    session: aiohttp.ClientSession,
) -> list[str]:

    sitemap_candidates = []

    # اول robots.txt
    try:

        sitemap_candidates.extend(
            await _get_sitemaps_from_robots(
                provider,
                session,
            )
        )

    except Exception:
        pass

    # sitemap تعریف‌شده
    sitemap = provider.get(
        "sitemap"
    )

    if sitemap:
        sitemap_candidates.append(
            sitemap
        )

    # موارد رایج
    base = (
        "https://"
        + provider["domain"]
    )

    for path in (
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/post-sitemap.xml",
        "/sitemap-index.xml",
    ):

        sitemap_candidates.append(
            base + path
        )

    # unique
    unique_sitemaps = []
    seen = set()

    for url in sitemap_candidates:

        if (
            url
            and url not in seen
            and _is_allowed_host(
                url,
                provider,
            )
        ):

            seen.add(url)
            unique_sitemaps.append(
                url
            )

    unique_sitemaps = unique_sitemaps[
        :MAX_SITEMAP_FILES
    ]

    all_urls = []
    seen_urls = set()

    processed_sitemaps = set()

    async def process_sitemap(
        sitemap_url: str,
    ):

        if (
            sitemap_url
            in processed_sitemaps
        ):
            return

        if len(
            processed_sitemaps
        ) >= MAX_SITEMAP_FILES:
            return

        processed_sitemaps.add(
            sitemap_url
        )

        xml = await _get_text(
            sitemap_url,
            session=session,
        )

        if not xml:
            return

        urls, children = (
            _parse_sitemap_urls(
                xml
            )
        )

        for url in urls:

            if (
                len(all_urls)
                >= MAX_SITEMAP_URLS
            ):
                break

            if not _is_allowed_host(
                url,
                provider,
            ):
                continue

            if url not in seen_urls:

                seen_urls.add(url)
                all_urls.append(url)

        # sitemap index
        for child in children:

            if (
                len(
                    processed_sitemaps
                )
                >= MAX_SITEMAP_FILES
            ):
                break

            if _is_allowed_host(
                child,
                provider,
            ):

                await process_sitemap(
                    child
                )

    for sitemap_url in unique_sitemaps:

        if (
            len(all_urls)
            >= MAX_SITEMAP_URLS
        ):
            break

        await process_sitemap(
            sitemap_url
        )

    return all_urls


# ============================================================
# SEARCH PAGE
# ============================================================

async def _search_provider_page(
    provider_key: str,
    query: str,
    session: aiohttp.ClientSession,
) -> list[dict]:

    provider = OFFICIAL_PROVIDERS[
        provider_key
    ]

    search_url = provider_search_url(
        provider_key,
        query,
    )

    if not search_url:
        return []

    html = await _get_text(
        search_url,
        session=session,
    )

    if not html:
        return []

    links = _absolute_links(
        search_url,
        html,
        provider,
    )

    results = []

    # --------------------------------------------------------
    # خود صفحه جستجو را هم بررسی کن
    # --------------------------------------------------------

    page_title = _page_title(
        html
    )

    if _is_good_match(
        query,
        page_title,
    ):

        results.append(
            {
                "id": provider_key,
                "name": provider[
                    "name"
                ],
                "url": search_url,
                "title": page_title,
                "year": None,
                "status": "search",
                "dub": False,
                "subtitle": False,
                "free": False,
                "paid": False,
            }
        )

    # --------------------------------------------------------
    # لینک‌های صفحه جستجو
    # --------------------------------------------------------

    for url in links:

        if len(results) >= MAX_PROVIDER_RESULTS:
            break

        # فقط لینک‌هایی که ظاهراً صفحه محتوا هستند
        low = url.lower()

        if any(
            bad in low
            for bad in (
                "/login",
                "/signup",
                "/register",
                "/account",
                "/category",
                "/tag/",
                "/search",
                "/page/",
            )
        ):
            continue

        page_html = await _get_text(
            url,
            session=session,
        )

        if not page_html:
            continue

        info = _extract_movie_info(
            page_html
        )

        title = (
            info.get("title")
            or ""
        )

        if not title:
            continue

        if not _is_good_match(
            query,
            title,
        ):
            continue

        results.append(
            {
                "id": provider_key,
                "name": provider[
                    "name"
                ],
                "url": url,
                "title": title,
                "year": info.get(
                    "year"
                ),
                "status": "found",
                "dub": False,
                "subtitle": False,
                "free": False,
                "paid": False,
            }
        )

    return results


# ============================================================
# SITEMAP SEARCH
# ============================================================

async def _search_provider_sitemap(
    provider_key: str,
    queries: list[str],
    session: aiohttp.ClientSession,
) -> list[dict]:

    provider = OFFICIAL_PROVIDERS[
        provider_key
    ]

    try:

        urls = await _collect_sitemap_urls(
            provider,
            session,
        )

    except Exception:

        logger.exception(
            "Sitemap collection failed: %s",
            provider_key,
        )

        return []

    if not urls:
        return []

    candidates = []

    normalized_queries = [
        _normalize_query(q)
        for q in queries
        if q
    ]

    tokens = set()

    for query in normalized_queries:
        tokens.update(
            _query_tokens(query)
        )

    # --------------------------------------------------------
    # ابتدا URL را فیلتر می‌کنیم تا مجبور نباشیم
    # تمام هزاران صفحه سایت را دانلود کنیم.
    # --------------------------------------------------------

    for url in urls:

        low = _normalize_query(
            url
        )

        score = 0

        for query in normalized_queries:

            score = max(
                score,
                _similarity_score(
                    query,
                    low,
                ),
            )

        if score >= 20:

            candidates.append(
                (
                    score,
                    url,
                )
            )

        elif tokens:

            matched = sum(
                1
                for token in tokens
                if token in low
            )

            if matched >= max(
                1,
                min(
                    2,
                    len(tokens),
                ),
            ):

                candidates.append(
                    (
                        matched * 10,
                        url,
                    )
                )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    candidates = candidates[
        :MAX_PROVIDER_RESULTS * 3
    ]

    results = []

    for _, url in candidates:

        if len(results) >= MAX_PROVIDER_RESULTS:
            break

        html = await _get_text(
            url,
            session=session,
        )

        if not html:
            continue

        info = _extract_movie_info(
            html
        )

        title = (
            info.get("title")
            or ""
        )

        if not title:
            continue

        best_score = 0

        for query in queries:

            best_score = max(
                best_score,
                _similarity_score(
                    query,
                    title,
                ),
            )

        if best_score < 35:
            continue

        results.append(
            {
                "id": provider_key,
                "name": provider[
                    "name"
                ],
                "url": url,
                "title": title,
                "year": info.get(
                    "year"
                ),
                "status": "sitemap",
                "dub": False,
                "subtitle": False,
                "free": False,
                "paid": False,
            }
        )

    return results


# ============================================================
# DEDUPLICATION
# ============================================================

def _dedupe_results(
    results: list[dict],
) -> list[dict]:

    unique = []
    seen = set()

    for item in results:

        url = (
            item.get("url")
            or ""
        )

        title = _normalize_query(
            item.get("title")
            or ""
        )

        key = (
            url.rstrip("/"),
            title,
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


# ============================================================
# SEARCH ONE PROVIDER
# ============================================================

async def _search_one_provider(
    provider_key: str,
    queries: list[str],
) -> list[dict]:

    connector = aiohttp.TCPConnector(
        limit=8,
        ttl_dns_cache=300,
    )

    async with aiohttp.ClientSession(
        timeout=TIMEOUT,
        connector=connector,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": (
                "fa-IR,fa;q=0.9,en;q=0.8"
            ),
        },
    ) as session:

        results = []

        # جستجوی مستقیم
        for query in queries:

            try:

                found = (
                    await _search_provider_page(
                        provider_key,
                        query,
                        session,
                    )
                )

                results.extend(
                    found
                )

            except Exception:

                logger.exception(
                    "Search page failed: %s / %s",
                    provider_key,
                    query,
                )

        # sitemap
        try:

            found = (
                await _search_provider_sitemap(
                    provider_key,
                    queries,
                    session,
                )
            )

            results.extend(
                found
            )

        except Exception:

            logger.exception(
                "Sitemap search failed: %s",
                provider_key,
            )

        return _dedupe_results(
            results
        )[
            :MAX_PROVIDER_RESULTS
        ]


# ============================================================
# SEARCH IRANIAN SOURCES
# ============================================================

async def search_iranian_sources(
    query: str,
    *,
    original_title: Optional[str] = None,
    year: Optional[str] = None,
) -> list[dict]:

    query = (
        query or ""
    ).strip()

    if not query:
        return []

    queries = _query_variants(
        query,
        original_title,
        year,
    )

    if not queries:
        return []

    tasks = []

    for key in OFFICIAL_PROVIDERS:

        tasks.append(
            _search_one_provider(
                key,
                queries,
            )
        )

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    final = []

    for item in results:

        if isinstance(
            item,
            Exception,
        ):

            logger.exception(
                "Provider task failed",
                exc_info=item,
            )

            continue

        final.extend(
            item
        )

    # --------------------------------------------------------
    # حذف تکراری‌ها
    # --------------------------------------------------------

    final = _dedupe_results(
        final
    )

    # --------------------------------------------------------
    # مرتب‌سازی:
    # اول نتیجه‌ای که عنوان دقیق‌تر دارد
    # --------------------------------------------------------

    def score(item):

        title = (
            item.get("title")
            or ""
        )

        best = 0

        for q in queries:

            best = max(
                best,
                _similarity_score(
                    q,
                    title,
                ),
            )

        return best

    final.sort(
        key=score,
        reverse=True,
    )

    return final


# ============================================================
# RESULT COMPATIBILITY
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

    provider = OFFICIAL_PROVIDERS[
        key
    ]

    return {
        "id": key,
        "name": provider[
            "name"
        ],
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
# TMDb
# ============================================================

async def _tmdb_get(
    path: str,
    params: Optional[dict] = None,
):

    if not TMDB_API_KEY:
        return None

    params = dict(
        params or {}
    )

    params[
        "api_key"
    ] = TMDB_API_KEY

    url = (
        TMDB_BASE_URL
        + path
    )

    async with aiohttp.ClientSession(
        timeout=TIMEOUT,
        headers={
            "User-Agent": USER_AGENT
        },
    ) as session:

        try:

            async with session.get(
                url,
                params=params,
            ) as response:

                if response.status != 200:

                    logger.warning(
                        "TMDb HTTP %s: %s",
                        response.status,
                        path,
                    )

                    return None

                return await response.json()

        except Exception:

            logger.exception(
                "TMDb request failed: %s",
                path,
            )

            return None


# ============================================================
# TMDb SEARCH
# ============================================================

async def search_movies(
    query: str,
    language: str = "fa-IR",
    limit: int = 10,
):

    query = (
        query or ""
    ).strip()

    if not query:
        return []

    if not TMDB_API_KEY:

        logger.warning(
            "TMDB_API_KEY is missing."
        )

        return []

    # --------------------------------------------------------
    # multi search:
    # هم فیلم و هم سریال
    # --------------------------------------------------------

    data = await _tmdb_get(
        "/search/multi",
        {
            "query": query,
            "language": language,
            "include_adult": "false",
            "page": 1,
        },
    )

    if not data:
        return []

    results = []

    for item in data.get(
        "results",
        [],
    ):

        media_type = item.get(
            "media_type"
        )

        if media_type not in (
            "movie",
            "tv",
        ):
            continue

        title = (
            item.get("title")
            if media_type == "movie"
            else item.get("name")
        )

        original_title = (
            item.get(
                "original_title"
            )
            if media_type == "movie"
            else item.get(
                "original_name"
            )
        )

        if not title:
            continue

        item[
            "_media_type"
        ] = media_type

        item[
            "_display_title"
        ] = title

        item[
            "_original_title"
        ] = original_title or ""

        results.append(
            item
        )

        if len(results) >= limit:
            break

    return results


# ============================================================
# WATCH PROVIDERS REPLACEMENT
# ============================================================

async def get_watch_providers(
    tmdb_id: int,
    media_type: str = "movie",
    region: Optional[str] = None,
):

    # region عمداً برای سازگاری با bot نگه داشته شده.
    # منابع ایرانی مستقل از TMDb Watch Providers هستند.

    if media_type not in (
        "movie",
        "tv",
    ):
        return None

    movie = await _tmdb_get(
        f"/{media_type}/{tmdb_id}",
        {
            "language": "fa-IR",
        },
    )

    if not movie:
        return None

    title = (
        movie.get("title")
        or movie.get("name")
        or ""
    )

    original_title = (
        movie.get(
            "original_title"
        )
        or movie.get(
            "original_name"
        )
        or ""
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
        str(date)[:4]
        if date
        else None
    )

    results = await search_iranian_sources(
        title,
        original_title=original_title,
        year=year,
    )

    return {
        "results": results,
        "link": None,
        "region": region or "IR",
    }


# ============================================================
# DISPLAY BADGES
# ============================================================

def _badges(
    item: dict,
) -> str:

    badges = []

    if item.get("free"):
        badges.append(
            "🆓 رایگان"
        )

    if item.get("paid"):
        badges.append(
            "💳 اشتراکی/خرید"
        )

    if item.get("dub"):
        badges.append(
            "🎙 دوبله"
        )

    if item.get("subtitle"):
        badges.append(
            "📝 زیرنویس"
        )

    if badges:
        return " • ".join(
            badges
        )

    return (
        "ℹ️ وضعیت هزینه و زبان "
        "در صفحه سرویس بررسی شود"
    )


# ============================================================
# PROVIDERS TEXT
# ============================================================

def providers_text(
    providers,
) -> str:

    # اگر خروجی get_watch_providers داده شده باشد
    if isinstance(
        providers,
        dict,
    ):
        providers = providers.get(
            "results",
            [],
        )

    if not providers:

        return (
            "😕 <b>نتیجه‌ای در منابع "
            "عمومی پیدا نشد.</b>"
        )

    lines = [
        "🇮🇷 <b>نتایج منابع عمومی</b>",
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

        title = escape(
            str(
                item.get(
                    "title",
                    "",
                )
            )
        )

        url = (
            item.get("url")
            or ""
        )

        year = (
            item.get("year")
            or "—"
        )

        if url:

            link = (
                f'<a href="{escape(url, quote=True)}">'
                "🔗 مشاهده صفحه"
                "</a>"
            )

        else:

            link = "🔗 لینک موجود نیست"

        lines.append(
            (
                f"\n🎬 <b>{name}</b>\n"
                f"   🎞 {title}\n"
                f"   📅 {year}\n"
                f"   {_badges(item)}\n"
                f"   {link}"
            )
        )

    return "\n".join(
        lines
    )


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
# EXPORT
# ============================================================

__all__ = [
    "search_iranian_sources",
    "search_movies",
    "get_watch_providers",
    "provider_search_url",
    "providers_text",
    "movie_text",
    "OFFICIAL_PROVIDERS",
    "_tmdb_get",
]
