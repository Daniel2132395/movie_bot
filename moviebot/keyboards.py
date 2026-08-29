# ============================================================
# MovieBot — Keyboards
# aiogram 3.x
# ============================================================

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from locales import t


# ============================================================
# LANGUAGE
# ============================================================

def lang_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇮🇷  فارسی", callback_data="lang:fa")
    b.button(text="🇬🇧  English", callback_data="lang:en")
    b.adjust(2)
    return b.as_markup()


# ============================================================
# MAIN MENU
# ============================================================

def main_menu_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    if lang == "fa":
        b.button(text="🎬  جستجو و تماشای فیلم", callback_data="menu:search_watch")
        b.button(text="🏆  برترین‌های IMDb", callback_data="menu:top250")
        b.button(text="🎭  ژانرها", callback_data="menu:genre")
        b.button(text="✨  پیشنهاد فیلم", callback_data="menu:recommend")
        b.button(text="⚖️  مقایسه فیلم", callback_data="menu:compare")
        b.button(text="🎭  جستجوی بازیگر", callback_data="menu:actor")
        b.button(text="🎬  جستجوی کارگردان", callback_data="menu:director")
        b.button(text="📅  فیلم‌های آینده", callback_data="menu:upcoming")
        b.button(text="🌐  زبان", callback_data="menu:lang")
        b.adjust(1, 2, 2, 2, 1, 1)
    else:
        b.button(text="🎬  Search & Watch", callback_data="menu:search_watch")
        b.button(text="🏆  IMDb Top", callback_data="menu:top250")
        b.button(text="🎭  Genres", callback_data="menu:genre")
        b.button(text="✨  Recommendations", callback_data="menu:recommend")
        b.button(text="⚖️  Compare", callback_data="menu:compare")
        b.button(text="🎭  Actor", callback_data="menu:actor")
        b.button(text="🎬  Director", callback_data="menu:director")
        b.button(text="📅  Upcoming", callback_data="menu:upcoming")
        b.button(text="🌐  Language", callback_data="menu:lang")
        b.adjust(1, 2, 2, 2, 1, 1)

    return b.as_markup()


# ============================================================
# SEARCH & WATCH
# ============================================================

def search_watch_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if lang == "fa":
        b.button(text="🔎  جستجوی فیلم یا سریال", callback_data="search:start")
        b.button(text="🌍  منطقه تماشا", callback_data="menu:region")
        b.button(text="🏠  منوی اصلی", callback_data="menu:home")
    else:
        b.button(text="🔎  Search Movie / Series", callback_data="search:start")
        b.button(text="🌍  Watch Region", callback_data="menu:region")
        b.button(text="🏠  Main Menu", callback_data="menu:home")
    b.adjust(1)
    return b.as_markup()


# ============================================================
# SEARCH RESULTS
# ============================================================

def search_results_kb(results: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    for movie in results:
        title = movie.get("title") or movie.get("name") or movie.get("original_title") or "بدون نام"
        title = str(title).strip()
        provider_id = movie.get("provider_id")
        if not provider_id:
            continue

        if len(title) > 42:
            title = title[:39] + "..."

        b.button(
            text=f"🎬  {title}",
            callback_data=f"provider:{provider_id}"
        )

    b.button(text="🏠  منوی اصلی", callback_data="menu:home")
    b.adjust(1)
    return b.as_markup()


# ============================================================
# MOVIE RESULT
# ============================================================

def movie_result_kb(provider_id: str, provider_url: str, query: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔗  ورود به صفحه رسمی سرویس", url=provider_url)
    b.button(text="🔎  جستجوی دوباره", callback_data="search:start")
    b.button(text="🏠  منوی اصلی", callback_data="menu:home")
    b.adjust(1)
    return b.as_markup()


# ============================================================
# REGION
# ============================================================

def region_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇮🇷  ایران", callback_data="region:IR")
    b.button(text="🇬🇧  بریتانیا", callback_data="region:GB")
    b.button(text="🇺🇸  آمریکا", callback_data="region:US")
    b.button(text="🇨🇦  کانادا", callback_data="region:CA")
    b.button(text="⬅️  بازگشت", callback_data="menu:home")
    b.adjust(2, 2, 1)
    return b.as_markup()


# ============================================================
# GENRE
# ============================================================

def genre_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    genres = [
        ("genre_romance", "Romance"),
        ("genre_drama", "Drama"),
        ("genre_comedy", "Comedy"),
        ("genre_action", "Action"),
        ("genre_scifi", "Sci-Fi"),
        ("genre_horror", "Horror"),
    ]
    for key, code in genres:
        b.button(text=t(key, lang), callback_data=f"genre:{code}")
    b.button(text=t("back", lang), callback_data="menu:home")
    b.adjust(2, 2, 2, 1)
    return b.as_markup()


# ============================================================
# MOOD
# ============================================================

def mood_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    moods = [
        ("mood_happy", "happy"),
        ("mood_thoughtful", "thoughtful"),
        ("mood_relax", "relax"),
        ("mood_intense", "intense"),
        ("mood_sad", "sad"),
    ]
    for key, code in moods:
        b.button(text=t(key, lang), callback_data=f"mood:{code}")
    b.button(text=t("back", lang), callback_data="menu:home")
    b.adjust(1)
    return b.as_markup()


# ============================================================
# QUIZ GENRE
# ============================================================

def quiz_genre_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    genres = [
        ("genre_romance", "Romance"),
        ("genre_drama", "Drama"),
        ("genre_comedy", "Comedy"),
        ("genre_action", "Action"),
        ("genre_scifi", "Sci-Fi"),
        ("genre_horror", "Horror"),
    ]
    for key, code in genres:
        b.button(text=t(key, lang), callback_data=f"qgenre:{code}")
    b.button(text=t("back", lang), callback_data="menu:home")
    b.adjust(2, 2, 2, 1)
    return b.as_markup()


# ============================================================
# MBTI
# ============================================================

def mbti_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    types = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
             "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"]
    for mt in types:
        b.button(text=mt, callback_data=f"mbti:{mt}")
    b.button(text=t("mbti_unknown", lang), callback_data="mbti:UNKNOWN")
    b.button(text=t("back", lang), callback_data="menu:home")
    b.adjust(4, 4, 4, 4, 1, 1)
    return b.as_markup()


# ============================================================
# BACK
# ============================================================

def back_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("back", lang), callback_data="menu:home")
    return b.as_markup()


# ============================================================
# SEARCH AGAIN
# ============================================================

def search_again_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔎  جستجوی دوباره", callback_data="search:start")
    b.button(text="🏠  منوی اصلی", callback_data="menu:home")
    b.adjust(1)
    return b.as_markup()


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    "lang_kb",
    "main_menu_kb",
    "search_watch_kb",
    "movie_result_kb",
    "search_results_kb",
    "region_kb",
    "genre_kb",
    "mood_kb",
    "quiz_genre_kb",
    "mbti_kb",
    "back_kb",
    "search_again_kb",
]
