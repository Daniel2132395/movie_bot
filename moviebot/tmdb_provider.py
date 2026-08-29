# tmdb_provider.py
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger("MovieBot.tmdb")

TMDB_API_KEY = ""  # اینجا کلیدت رو بذار
TMDB_BASE_URL = "https://api.themoviedb.org/3"


async def search_tmdb(query: str, media_type: str = "all") -> list:
    """جستجو در TMDB API"""
    if not TMDB_API_KEY:
        logger.error("TMDB_API_KEY is not set!")
        return []
    
    results = []
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{TMDB_BASE_URL}/search/multi"
            params = {
                "api_key": TMDB_API_KEY,
                "query": query,
                "language": "fa-IR",
                "page": 1,
            }
            
            async with session.get(url, params=params, timeout=15) as response:
                if response.status != 200:
                    logger.error(f"TMDB error: {response.status}")
                    return []
                
                data = await response.json()
                
                for item in data.get("results", [])[:10]:
                    # فقط فیلم و سریال
                    if item.get("media_type") not in ["movie", "tv"]:
                        continue
                    
                    # دریافت جزئیات کامل
                    detail_url = f"{TMDB_BASE_URL}/{item.get('media_type')}/{item.get('id')}"
                    detail_params = {
                        "api_key": TMDB_API_KEY,
                        "language": "fa-IR",
                    }
                    
                    try:
                        async with session.get(detail_url, params=detail_params, timeout=10) as detail_response:
                            detail = await detail_response.json()
                            
                            title = detail.get("title") or detail.get("name") or item.get("name", query)
                            overview = detail.get("overview") or item.get("overview", "اطلاعاتی موجود نیست.")
                            poster = detail.get("poster_path") or item.get("poster_path", "")
                            release_date = detail.get("release_date") or detail.get("first_air_date") or ""
                            vote_average = detail.get("vote_average", 0)
                            year = release_date[:4] if release_date else "N/A"
                            
                            results.append({
                                "id": item.get("id"),
                                "title": title,
                                "name": title,
                                "original_title": detail.get("original_title") or detail.get("original_name", title),
                                "_media_type": item.get("media_type"),
                                "provider_id": "tmdb",
                                "provider_name": "🎬 TMDB",
                                "provider_url": f"https://www.themoviedb.org/{item.get('media_type')}/{item.get('id')}",
                                "url": f"https://www.themoviedb.org/{item.get('media_type')}/{item.get('id')}",
                                "release_date": year,
                                "vote_average": vote_average,
                                "overview": overview[:500] + "..." if len(overview) > 500 else overview,
                                "poster": poster,
                            })
                    except Exception as e:
                        logger.error(f"TMDB detail error: {e}")
                        
                        # اگر جزئیات نیومد، همون اطلاعات اولیه رو برگردون
                        results.append({
                            "id": item.get("id"),
                            "title": item.get("name") or item.get("title", query),
                            "name": item.get("name") or item.get("title", query),
                            "original_title": item.get("name") or item.get("title", query),
                            "_media_type": item.get("media_type"),
                            "provider_id": "tmdb",
                            "provider_name": "🎬 TMDB",
                            "provider_url": f"https://www.themoviedb.org/{item.get('media_type')}/{item.get('id')}",
                            "url": f"https://www.themoviedb.org/{item.get('media_type')}/{item.get('id')}",
                            "release_date": "",
                            "vote_average": 0,
                            "overview": item.get("overview", "اطلاعاتی موجود نیست.")[:500],
                            "poster": item.get("poster_path", ""),
                        })
    except Exception as e:
        logger.error(f"TMDB search error: {e}")
    
    return results
