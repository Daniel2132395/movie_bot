# download_links.py
import aiohttp
import logging
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

logger = logging.getLogger("MovieBot.download")

# ============================================================
# سرویس‌های دانلود
# ============================================================

DOWNLOAD_SERVICES = {
    "film2movie": {
        "name": "🎬 فیلم تو مووی",
        "domain": "film2movie.ir",
        "search_url": "https://www.film2movie.ir/search/{query}",
        "type": "دانلود",
    },
    "nimafilm": {
        "name": "🎬 نیما فیلم",
        "domain": "nimafilm.ir",
        "search_url": "https://www.nimafilm.ir/search/{query}",
        "type": "دانلود",
    },
    "filmgram": {
        "name": "🎬 فیلم گرام",
        "domain": "filmgram.com",
        "search_url": "https://www.filmgram.com/search/{query}",
        "type": "دانلود",
    },
    "moviebox": {
        "name": "🎬 مووی باکس",
        "domain": "moviebox.ir",
        "search_url": "https://moviebox.ir/search/{query}",
        "type": "دانلود",
    },
    "720p": {
        "name": "🎬 ۷۲۰پی",
        "domain": "720p.ir",
        "search_url": "https://720p.ir/search/{query}",
        "type": "دانلود",
    },
    "hdvideo": {
        "name": "🎬 اچ‌دی ویدیو",
        "domain": "hdvideo.ir",
        "search_url": "https://hdvideo.ir/search/{query}",
        "type": "دانلود",
    },
}


# ============================================================
# سرویس‌های تماشا آنلاین
# ============================================================

WATCH_SERVICES = {
    "telewebion": {
        "name": "▶️ تلوبیون",
        "domain": "telewebion.com",
        "search_url": "https://www.telewebion.com/search?q={query}",
        "type": "تماشا آنلاین",
    },
    "aparat": {
        "name": "▶️ آپارات",
        "domain": "aparat.com",
        "search_url": "https://www.aparat.com/search/{query}",
        "type": "تماشا آنلاین",
    },
    "tamasha": {
        "name": "▶️ تماشا",
        "domain": "tamasha.com",
        "search_url": "https://www.tamasha.com/search?q={query}",
        "type": "تماشا آنلاین",
    },
    "namava": {
        "name": "▶️ نماوا",
        "domain": "namava.ir",
        "search_url": "https://www.namava.ir/search?q={query}",
        "type": "تماشا آنلاین",
    },
    "filimo": {
        "name": "▶️ فیلیمو",
        "domain": "filimo.com",
        "search_url": "https://www.filimo.com/search?q={query}",
        "type": "تماشا آنلاین",
    },
}


# ============================================================
# جستجوی لینک دانلود
# ============================================================

async def search_download_links(query: str):
    """جستجوی لینک دانلود از سایت‌های معتبر"""
    query = query.strip()
    if not query:
        return []
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for key, service in DOWNLOAD_SERVICES.items():
            try:
                search_url = service["search_url"].format(query=quote_plus(query))
                
                async with session.get(
                    search_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
                    },
                    timeout=10,
                    allow_redirects=True,
                ) as response:
                    if response.status != 200:
                        continue
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # پیدا کردن لینک‌های فیلم
                    links = soup.find_all("a", href=True)
                    
                    for link in links[:5]:
                        href = link.get("href", "")
                        text = link.get_text(strip=True)
                        
                        if not href or not text or len(text) < 3:
                            continue
                        
                        # ساخت URL کامل
                        if href.startswith("/"):
                            href = f"https://{service['domain']}{href}"
                        elif not href.startswith("http"):
                            href = f"https://{service['domain']}/{href}"
                        
                        # بررسی اینکه لینک به صفحه فیلم اشاره دارد
                        if any(x in href.lower() for x in ["/movie/", "/film/", "/video/", "/watch/", "/download/"]):
                            results.append({
                                "title": text[:50],
                                "url": href,
                                "service": service["name"],
                                "type": service["type"],
                                "domain": service["domain"],
                            })
                        
                        if len(results) >= 20:
                            break
                            
            except Exception as e:
                logger.error(f"Error searching {key}: {e}")
                continue
    
    return results[:20]


# ============================================================
# جستجوی لینک تماشا آنلاین
# ============================================================

async def search_watch_links(query: str):
    """جستجوی لینک تماشا آنلاین از سرویس‌های مختلف"""
    query = query.strip()
    if not query:
        return []
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for key, service in WATCH_SERVICES.items():
            try:
                search_url = service["search_url"].format(query=quote_plus(query))
                
                async with session.get(
                    search_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
                    },
                    timeout=10,
                    allow_redirects=True,
                ) as response:
                    if response.status != 200:
                        continue
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    links = soup.find_all("a", href=True)
                    
                    for link in links[:5]:
                        href = link.get("href", "")
                        text = link.get_text(strip=True)
                        
                        if not href or not text or len(text) < 3:
                            continue
                        
                        if href.startswith("/"):
                            href = f"https://{service['domain']}{href}"
                        elif not href.startswith("http"):
                            href = f"https://{service['domain']}/{href}"
                        
                        results.append({
                            "title": text[:50],
                            "url": href,
                            "service": service["name"],
                            "type": service["type"],
                            "domain": service["domain"],
                        })
                        
                        if len(results) >= 20:
                            break
                            
            except Exception as e:
                logger.error(f"Error searching {key}: {e}")
                continue
    
    return results[:20]
