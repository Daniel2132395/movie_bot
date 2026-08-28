from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from locales import t

# Note: Telegram bot messages render with the native Telegram theme — there
# is no CSS, so a literal "glassmorphism" panel isn't possible in a plain
# bot chat. We get as close to that "clean glass panel" feel as Telegram
# allows: a tightly grouped, rounded inline-keyboard "button box" under
# every message (Telegram renders inline buttons with soft rounded corners
# and a translucent highlight on tap, matching iOS/Android's own glass
# style). For genuinely custom glass/blur UI, see the README section on
# Telegram Mini Apps (Web Apps), which do support full HTML/CSS.


def lang_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇮🇷 فارسی", callback_data="lang:fa")
    b.button(text="🇬🇧 English", callback_data="lang:en")
    b.adjust(2)
    return b.as_markup()


def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("menu_top250", lang), callback_data="menu:top250")
    b.button(text=t("menu_genre", lang), callback_data="menu:genre")
    b.button(text=t("menu_recommend", lang), callback_data="menu:recommend")
    b.button(text=t("menu_compare", lang), callback_data="menu:compare")
    b.button(text=t("menu_actor", lang), callback_data="menu:actor")
    b.button(text=t("menu_director", lang), callback_data="menu:director")
    b.button(text=t("menu_upcoming", lang), callback_data="menu:upcoming")
    b.button(text=t("menu_lang", lang), callback_data="menu:lang")
    b.adjust(1, 1, 1, 1, 2, 1, 1)
    return b.as_markup()


def genre_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    genres = [
        ("genre_romance", "Romance"), ("genre_drama", "Drama"),
        ("genre_comedy", "Comedy"), ("genre_action", "Action"),
        ("genre_scifi", "Sci-Fi"), ("genre_horror", "Horror"),
    ]
    for key, code in genres:
        b.button(text=t(key, lang), callback_data=f"genre:{code}")
    b.button(text=t("back", lang), callback_data="menu:home")
    b.adjust(2, 2, 2, 1)
    return b.as_markup()


def mood_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, code in [("mood_happy", "happy"), ("mood_thoughtful", "thoughtful"),
                       ("mood_relax", "relax"), ("mood_intense", "intense"),
                       ("mood_sad", "sad")]:
        b.button(text=t(key, lang), callback_data=f"mood:{code}")
    b.adjust(1)
    return b.as_markup()


def quiz_genre_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, code in [("genre_romance", "Romance"), ("genre_drama", "Drama"),
                       ("genre_comedy", "Comedy"), ("genre_action", "Action"),
                       ("genre_scifi", "Sci-Fi"), ("genre_horror", "Horror")]:
        b.button(text=t(key, lang), callback_data=f"qgenre:{code}")
    b.adjust(2)
    return b.as_markup()


def mbti_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    types = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
             "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"]
    for mt in types:
        b.button(text=mt, callback_data=f"mbti:{mt}")
    b.button(text=t("mbti_unknown", lang), callback_data="mbti:UNKNOWN")
    b.adjust(4, 4, 4, 4, 1)
    return b.as_markup()


def back_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("back", lang), callback_data="menu:home")
    return b.as_markup()
