from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from locales import t


# ============================================================
# LANGUAGE
# ============================================================

def lang_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    b.button(
        text="🇮🇷 فارسی",
        callback_data="lang:fa",
    )

    b.button(
        text="🇬🇧 English",
        callback_data="lang:en",
    )

    b.adjust(2)

    return b.as_markup()


# ============================================================
# MAIN MENU
# ============================================================

def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    # ⭐ بخش اصلی جستجو و تماشا
    b.button(
        text="🎬 جستجو و تماشای فیلم",
        callback_data="menu:search_watch",
    )

    b.button(
        text=t("menu_top250", lang),
        callback_data="menu:top250",
    )

    b.button(
        text=t("menu_genre", lang),
        callback_data="menu:genre",
    )

    b.button(
        text=t("menu_recommend", lang),
        callback_data="menu:recommend",
    )

    b.button(
        text=t("menu_compare", lang),
        callback_data="menu:compare",
    )

    b.button(
        text=t("menu_actor", lang),
        callback_data="menu:actor",
    )

    b.button(
        text=t("menu_director", lang),
        callback_data="menu:director",
    )

    b.button(
        text=t("menu_upcoming", lang),
        callback_data="menu:upcoming",
    )

    b.button(
        text=t("menu_lang", lang),
        callback_data="menu:lang",
    )

    # چیدمان منوی اصلی
    b.adjust(
        1,      # جستجو و تماشا
        2,      # برترین‌ها + ژانر
        2,      # پیشنهاد + مقایسه
        2,      # بازیگر + کارگردان
        1,      # اکران
        1,      # زبان
    )

    return b.as_markup()


# ============================================================
# SEARCH & WATCH MENU
# ============================================================

def search_watch_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    b.button(
        text="🔎 جستجوی فیلم یا سریال",
        callback_data="search:start",
    )

    b.button(
        text="🌍 منطقه تماشا",
        callback_data="menu:region",
    )

    b.button(
        text="🏠 منوی اصلی",
        callback_data="menu:home",
    )

    b.adjust(1)

    return b.as_markup()


# ============================================================
# SEARCH RESULT MENU
# ============================================================

def movie_result_kb(
    tmdb_id: int,
    media_type: str,
) -> InlineKeyboardMarkup:

    b = InlineKeyboardBuilder()

    b.button(
        text="📺 گزینه‌های قانونی تماشا",
        callback_data=f"watch:{media_type}:{tmdb_id}",
    )

    b.button(
        text="🔎 جستجوی دوباره",
        callback_data="search:start",
    )

    b.button(
        text="🏠 خانه",
        callback_data="menu:home",
    )

    b.adjust(
        1,
        2,
    )

    return b.as_markup()


# ============================================================
# SEARCH RESULT LIST
# ============================================================

def search_results_kb(
    results: list,
) -> InlineKeyboardMarkup:

    b = InlineKeyboardBuilder()

    for movie in results:

        title = (
            movie.get("title")
            or movie.get("name")
            or movie.get("original_title")
            or "بدون نام"
        )

        media_type = movie.get(
            "_media_type",
            "movie",
        )

        tmdb_id = movie.get("id")

        if not tmdb_id:
            continue

        icon = (
            "📺"
            if media_type == "tv"
            else "🎬"
        )

        b.button(
            text=f"{icon} {title[:45]}",
            callback_data=(
                f"result:{media_type}:{tmdb_id}"
            ),
        )

    b.button(
        text="🏠 منوی اصلی",
        callback_data="menu:home",
    )

    b.adjust(1)

    return b.as_markup()


# ============================================================
# WATCH PROVIDERS
# ============================================================

def watch_kb(
    media_type: str,
    tmdb_id: int,
    provider_link: str | None = None,
) -> InlineKeyboardMarkup:

    b = InlineKeyboardBuilder()

    # فقط اگر TMDb لینک رسمی provider داشته باشد
    if provider_link:

        b.button(
            text="🔗 مشاهده سرویس‌های رسمی",
            url=provider_link,
        )

    b.button(
        text="🌍 تغییر منطقه",
        callback_data="menu:region",
    )

    b.button(
        text="⬅️ بازگشت به فیلم",
        callback_data=(
            f"result:{media_type}:{tmdb_id}"
        ),
    )

    b.button(
        text="🏠 منوی اصلی",
        callback_data="menu:home",
    )

    if provider_link:
        b.adjust(
            1,
            2,
            1,
        )
    else:
        b.adjust(
            2,
            1,
        )

    return b.as_markup()


# ============================================================
# REGION
# ============================================================

def region_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    b.button(
        text="🇮🇷 ایران",
        callback_data="region:IR",
    )

    b.button(
        text="🇬🇧 بریتانیا",
        callback_data="region:GB",
    )

    b.button(
        text="🇺🇸 آمریکا",
        callback_data="region:US",
    )

    b.button(
        text="🇨🇦 کانادا",
        callback_data="region:CA",
    )

    b.button(
        text="⬅️ بازگشت",
        callback_data="menu:home",
    )

    b.adjust(
        2,
        2,
        1,
    )

    return b.as_markup()


# ============================================================
# GENRE
# ============================================================

def genre_kb(lang: str) -> InlineKeyboardMarkup:
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

        b.button(
            text=t(key, lang),
            callback_data=f"genre:{code}",
        )

    b.button(
        text=t("back", lang),
        callback_data="menu:home",
    )

    b.adjust(
        2,
        2,
        2,
        1,
    )

    return b.as_markup()


# ============================================================
# MOOD
# ============================================================

def mood_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    moods = [
        ("mood_happy", "happy"),
        ("mood_thoughtful", "thoughtful"),
        ("mood_relax", "relax"),
        ("mood_intense", "intense"),
        ("mood_sad", "sad"),
    ]

    for key, code in moods:

        b.button(
            text=t(key, lang),
            callback_data=f"mood:{code}",
        )

    b.adjust(1)

    return b.as_markup()


# ============================================================
# QUIZ GENRE
# ============================================================

def quiz_genre_kb(lang: str) -> InlineKeyboardMarkup:
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

        b.button(
            text=t(key, lang),
            callback_data=f"qgenre:{code}",
        )

    b.adjust(2)

    return b.as_markup()


# ============================================================
# MBTI
# ============================================================

def mbti_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    types = [
        "INTJ",
        "INTP",
        "ENTJ",
        "ENTP",
        "INFJ",
        "INFP",
        "ENFJ",
        "ENFP",
        "ISTJ",
        "ISFJ",
        "ESTJ",
        "ESFJ",
        "ISTP",
        "ISFP",
        "ESTP",
        "ESFP",
    ]

    for mt in types:

        b.button(
            text=mt,
            callback_data=f"mbti:{mt}",
        )

    b.button(
        text=t("mbti_unknown", lang),
        callback_data="mbti:UNKNOWN",
    )

    b.adjust(
        4,
        4,
        4,
        4,
        1,
    )

    return b.as_markup()


# ============================================================
# BACK
# ============================================================

def back_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    b.button(
        text=t("back", lang),
        callback_data="menu:home",
    )

    return b.as_markup()
