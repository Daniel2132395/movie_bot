# bot.py
# ============================================================
# MovieBot
# aiogram 3.x + TMDb + SQLite
# ============================================================

import asyncio
import logging
import os
from threading import Thread
from html import escape
from urllib.parse import quote_plus

import aiohttp
from flask import Flask

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from dotenv import load_dotenv

from data.imdb_top import IMDB_TOP
from data.genre_extra import GENRE_EXTRA
from data.people import ACTORS, DIRECTORS
from data.upcoming import UPCOMING

from keyboards import (
    back_kb,
    genre_kb,
    lang_kb,
    main_menu_kb,
    mbti_kb,
    mood_kb,
    quiz_genre_kb,
)

from locales import t
from recommender import recommend

from movie_db import (
    init_movie_db,
    save_movie,
    search_local_movies,
)

from providers import (
    search_movies,
    get_watch_providers,
    movie_text,
    providers_text,
)


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("MovieBot")

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
).strip()

OMDB_API_KEY = os.getenv(
    "OMDB_API_KEY",
    "",
).strip()

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    "",
).strip()

# منطقه پیش‌فرض
# IR = ایران
# GB = بریتانیا
# US = آمریکا
DEFAULT_REGION = os.getenv(
    "WATCH_REGION",
    "IR",
).strip().upper()


# ============================================================
# FLASK / RENDER HEALTH SERVER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "MovieBot is running!", 200


@app.route("/health")
def health():
    return "OK", 200


def run_web_server():

    port = int(
        os.getenv(
            "PORT",
            "8080",
        )
    )

    logger.info(
        "Starting web server on port %s",
        port,
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )


def keep_alive():

    thread = Thread(
        target=run_web_server,
        daemon=True,
    )

    thread.start()


# ============================================================
# ROUTER
# ============================================================

router = Router()


# ============================================================
# USER LANGUAGE
# ============================================================

USER_LANG: dict[int, str] = {}


def lang_of(user_id: int) -> str:

    return USER_LANG.get(
        user_id,
        "fa",
    )


# ============================================================
# USER REGION
# ============================================================

USER_REGION: dict[int, str] = {}


def region_of(user_id: int) -> str:

    return USER_REGION.get(
        user_id,
        DEFAULT_REGION,
    )


# ============================================================
# STATES
# ============================================================

class Quiz(StatesGroup):

    mood = State()
    genre = State()
    mbti = State()
    liked = State()
    disliked = State()


class TextSearch(StatesGroup):

    actor = State()
    director = State()
    movie = State()


class MovieSearch(StatesGroup):

    query = State()


# ============================================================
# CLEAN TEXT
# ============================================================

def clean(text: str) -> str:

    if not text:
        return ""

    return escape(
        str(text)
    )


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    user_id = message.from_user.id

    if user_id not in USER_LANG:
        USER_LANG[user_id] = "fa"

    lang = lang_of(user_id)

    await message.answer(
        t(
            "welcome",
            lang,
        ),
        reply_markup=main_menu_kb(lang),
    )


# ============================================================
# CANCEL
# ============================================================

@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    lang = lang_of(
        message.from_user.id
    )

    await message.answer(
        t(
            "cancelled",
            lang,
        )
    )

    await message.answer(
        t(
            "welcome",
            lang,
        ),
        reply_markup=main_menu_kb(lang),
    )


# ============================================================
# LANGUAGE
# ============================================================

@router.callback_query(
    F.data.startswith("lang:")
)
async def set_lang(
    call: CallbackQuery,
    state: FSMContext,
):

    lang = call.data.split(
        ":",
        1,
    )[1]

    USER_LANG[
        call.from_user.id
    ] = lang

    await state.clear()

    await call.message.edit_text(
        t(
            "welcome",
            lang,
        ),
        reply_markup=main_menu_kb(lang),
    )

    await call.answer()


@router.callback_query(
    F.data == "menu:lang"
)
async def menu_lang(
    call: CallbackQuery,
):

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        t(
            "choose_lang",
            lang,
        ),
        reply_markup=lang_kb(),
    )

    await call.answer()


@router.callback_query(
    F.data == "menu:home"
)
async def menu_home(
    call: CallbackQuery,
    state: FSMContext,
):

    await state.clear()

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        t(
            "welcome",
            lang,
        ),
        reply_markup=main_menu_kb(lang),
    )

    await call.answer()


# ============================================================
# REGION SELECTOR
# ============================================================

def region_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🇮🇷 ایران",
                    callback_data="region:IR",
                ),
                InlineKeyboardButton(
                    text="🇬🇧 بریتانیا",
                    callback_data="region:GB",
                ),
            ],

            [
                InlineKeyboardButton(
                    text="🇺🇸 آمریکا",
                    callback_data="region:US",
                ),
                InlineKeyboardButton(
                    text="🇨🇦 کانادا",
                    callback_data="region:CA",
                ),
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ بازگشت",
                    callback_data="menu:home",
                ),
            ],
        ]
    )


@router.callback_query(
    F.data == "menu:region"
)
async def choose_region(
    call: CallbackQuery,
):

    lang = lang_of(
        call.from_user.id
    )

    text = (
        "🌍 <b>منطقه تماشا</b>\n\n"
        "کشور خودت را انتخاب کن تا "
        "سرویس‌های موجود برای همان منطقه "
        "بررسی شوند."
    )

    await call.message.edit_text(
        text,
        reply_markup=region_keyboard(),
    )

    await call.answer()


@router.callback_query(
    F.data.startswith("region:")
)
async def set_region(
    call: CallbackQuery,
):

    region = call.data.split(
        ":",
        1,
    )[1].upper()

    USER_REGION[
        call.from_user.id
    ] = region

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        (
            "✅ <b>منطقه ذخیره شد</b>\n\n"
            f"🌍 منطقه: <b>{region}</b>\n\n"
            "از این به بعد گزینه‌های تماشا "
            "بر اساس این منطقه بررسی می‌شوند."
        ),
        reply_markup=main_menu_kb(lang),
    )

    await call.answer(
        "ذخیره شد ✅"
    )


# ============================================================
# MOVIE SEARCH MENU
# ============================================================

def search_menu_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🔎 جستجوی فیلم یا سریال",
                    callback_data="search:start",
                ),
            ],

            [
                InlineKeyboardButton(
                    text="🌍 تغییر منطقه",
                    callback_data="menu:region",
                ),
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ منوی اصلی",
                    callback_data="menu:home",
                ),
            ],
        ]
    )


@router.callback_query(
    F.data == "search:start"
)
async def search_start(
    call: CallbackQuery,
    state: FSMContext,
):

    await state.clear()

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        (
            "🔎 <b>جستجوی فیلم و سریال</b>\n\n"
            "نام فیلم یا سریال را بفرست.\n\n"
            "مثلاً:\n"
            "🎬 Interstellar\n"
            "📺 Breaking Bad"
        ),
        reply_markup=search_menu_keyboard(),
    )

    await state.set_state(
        MovieSearch.query
    )

    await call.answer()


# ============================================================
# SHOW MOVIE RESULT
# ============================================================

def movie_result_keyboard(
    tmdb_id: int,
    media_type: str,
):

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📺 گزینه‌های تماشا",
                    callback_data=(
                        f"watch:{media_type}:{tmdb_id}"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    text="🔎 جستجوی دوباره",
                    callback_data="search:start",
                ),

                InlineKeyboardButton(
                    text="🏠 خانه",
                    callback_data="menu:home",
                ),
            ],
        ]
    )


async def send_movie_result(
    message: Message,
    movie: dict,
):

    tmdb_id = movie.get(
        "id"
    )

    media_type = movie.get(
        "_media_type",
        "movie",
    )

    if not tmdb_id:
        await message.answer(
            "❌ نتیجه نامعتبر بود."
        )
        return

    # ذخیره در دیتابیس
    try:

        save_movie(movie)

    except Exception:

        logger.exception(
            "Could not save movie"
        )

    text = movie_text(
        movie
    )

    await message.answer(
        text,
        reply_markup=movie_result_keyboard(
            tmdb_id,
            media_type,
        ),
    )


# ============================================================
# SEARCH HANDLER
# ============================================================

@router.message(
    MovieSearch.query
)
async def movie_search(
    message: Message,
    state: FSMContext,
):

    query = (
        message.text or ""
    ).strip()

    if not query:

        await message.answer(
            "❌ لطفاً نام فیلم یا سریال را بفرست."
        )

        return

    lang = lang_of(
        message.from_user.id
    )

    await message.answer(
        "🔎 <b>در حال جستجو...</b>\n\n"
        "یک لحظه صبر کن 🎬"
    )

    try:

        results = await search_movies(
            query,
            language=(
                "fa-IR"
                if lang == "fa"
                else "en-US"
            ),
            limit=8,
        )

    except Exception:

        logger.exception(
            "Movie search failed"
        )

        await message.answer(
            "⚠️ جستجو موقتاً با مشکل مواجه شد."
        )

        await state.clear()

        return

    if not results:

        await message.answer(
            (
                "😕 <b>چیزی پیدا نشد</b>\n\n"
                f"🔎 جستجو: <b>{clean(query)}</b>\n\n"
                "نام دیگری را امتحان کن."
            ),
            reply_markup=search_menu_keyboard(),
        )

        await state.clear()

        return

    # اگر چند نتیجه داریم
    buttons = []

    for movie in results:

        title = (
            movie.get("title")
            or movie.get("name")
            or "بدون نام"
        )

        media_type = movie.get(
            "_media_type",
            "movie",
        )

        tmdb_id = movie.get(
            "id"
        )

        icon = (
            "📺"
            if media_type == "tv"
            else "🎬"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{icon} "
                        f"{title[:45]}"
                    ),
                    callback_data=(
                        f"result:{media_type}:{tmdb_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ بازگشت",
                callback_data="menu:home",
            )
        ]
    )

    await message.answer(
        (
            "🎬 <b>نتایج جستجو</b>\n\n"
            f"🔎 «{clean(query)}»\n\n"
            "یکی را انتخاب کن:"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
    )

    await state.clear()


# ============================================================
# RESULT SELECT
# ============================================================

@router.callback_query(
    F.data.startswith("result:")
)
async def result_select(
    call: CallbackQuery,
):

    parts = call.data.split(
        ":"
    )

    if len(parts) != 3:

        await call.answer(
            "نتیجه نامعتبر است.",
            show_alert=True,
        )

        return

    media_type = parts[1]

    try:

        tmdb_id = int(
            parts[2]
        )

    except ValueError:

        await call.answer(
            "شناسه نامعتبر است.",
            show_alert=True,
        )

        return

    # جستجوی محلی برای پیدا کردن نتیجه
    # در صورت نبودن، دوباره جستجوی TMDb انجام می‌شود.

    movie = None

    try:

        from providers import _tmdb_get

        movie = await _tmdb_get(
            f"/{media_type}/{tmdb_id}",
            {
                "language": (
                    "fa-IR"
                    if lang_of(
                        call.from_user.id
                    ) == "fa"
                    else "en-US"
                )
            },
        )

    except Exception:

        logger.exception(
            "Could not get movie details"
        )

    if not movie:

        await call.answer(
            "اطلاعات پیدا نشد.",
            show_alert=True,
        )

        return

    movie["_media_type"] = (
        media_type
    )

    try:

        save_movie(
            movie
        )

    except Exception:

        logger.exception(
            "Could not save movie"
        )

    await call.message.edit_text(
        movie_text(
            movie
        ),
        reply_markup=movie_result_keyboard(
            tmdb_id,
            media_type,
        ),
    )

    await call.answer()


# ============================================================
# WATCH PROVIDERS
# ============================================================

@router.callback_query(
    F.data.startswith("watch:")
)
async def watch_providers(
    call: CallbackQuery,
):

    parts = call.data.split(
        ":"
    )

    if len(parts) != 3:

        await call.answer(
            "اطلاعات نامعتبر است.",
            show_alert=True,
        )

        return

    media_type = parts[1]

    try:

        tmdb_id = int(
            parts[2]
        )

    except ValueError:

        await call.answer(
            "شناسه نامعتبر است.",
            show_alert=True,
        )

        return

    region = region_of(
        call.from_user.id
    )

    await call.answer(
        "📺 در حال بررسی سرویس‌ها..."
    )

    try:

        providers = await get_watch_providers(
            tmdb_id=tmdb_id,
            media_type=media_type,
            region=region,
        )

    except Exception:

        logger.exception(
            "Provider request failed"
        )

        await call.message.answer(
            "⚠️ دریافت سرویس‌های تماشا با مشکل مواجه شد."
        )

        return

    if not providers:

        text = (
            "📺 <b>گزینه‌های تماشا</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"🌍 منطقه: <b>{region}</b>\n\n"
            "😕 برای این عنوان در این منطقه "
            "سرویس قانونی ثبت‌شده‌ای پیدا نشد.\n\n"
            "💡 می‌توانی منطقه تماشا را تغییر بدهی."
        )

    else:

        text = (
            "📺 <b>گزینه‌های تماشا</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            + providers_text(
                providers
            )
        )

        text += (
            "\n\n"
            "ℹ️ اطلاعات سرویس‌ها از داده‌های "
            "Watch Providers در TMDb است."
        )

    buttons = []

    # لینک رسمی TMDb / JustWatch
    provider_link = (
        providers.get("link")
        if providers
        else None
    )

    if provider_link:

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔗 مشاهده گزینه‌های رسمی",
                    url=provider_link,
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="🌍 تغییر منطقه",
                    callback_data="menu:region",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ بازگشت به فیلم",
                    callback_data=(
                        f"result:{media_type}:{tmdb_id}"
                    ),
                ),
            ],
        ]
    )

    await call.message.edit_text(
        text[:4090],
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
    )


# ============================================================
# TOP IMDb
# ============================================================

def _fmt_entry(
    idx,
    title,
    year,
    kind,
    imdb,
    rt,
    meta,
    lang,
):

    if kind == "series":

        kind_label = (
            "سریال"
            if lang == "fa"
            else "Series"
        )

    else:

        kind_label = (
            "فیلم"
            if lang == "fa"
            else "Movie"
        )

    rt_s = (
        f"{rt}%"
        if rt is not None
        else "—"
    )

    meta_s = (
        f"{meta}"
        if meta is not None
        else "—"
    )

    return (
        f"🎬 <b>{clean(title)}</b> "
        f"({year})\n"
        f"   {kind_label} • "
        f"⭐ IMDb {imdb} • "
        f"🍅 RT {rt_s} • "
        f"Ⓜ️ {meta_s}"
    )


@router.callback_query(
    F.data == "menu:top250"
)
async def top250(
    call: CallbackQuery,
):

    lang = lang_of(
        call.from_user.id
    )

    sorted_list = sorted(
        IMDB_TOP,
        key=lambda r: -r[4],
    )

    lines = []

    for i, r in enumerate(
        sorted_list[:40],
        1,
    ):

        lines.append(
            _fmt_entry(
                i,
                r[1],
                r[2],
                r[3],
                r[4],
                r[5],
                r[6],
                lang,
            )
        )

    text = (
        "🏆 <b>برترین‌های IMDb</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(
            lines
        )
        + "\n\n"
        "💡 برای دیدن گزینه‌های تماشا، "
        "هر عنوان را جداگانه جستجو کن."
    )

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_kb(
            lang
        ),
    )

    await call.answer()


# ============================================================
# GENRES
# ============================================================

@router.callback_query(
    F.data == "menu:genre"
)
async def menu_genre(
    call: CallbackQuery,
):

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        t(
            "pick_genre",
            lang,
        ),
        reply_markup=genre_kb(
            lang
        ),
    )

    await call.answer()


@router.callback_query(
    F.data.startswith("genre:")
)
async def show_genre(
    call: CallbackQuery,
):

    lang = lang_of(
        call.from_user.id
    )

    genre = call.data.split(
        ":",
        1,
    )[1]

    items = []

    for r in IMDB_TOP:

        if genre in r[7]:

            items.append(
                (
                    r[1],
                    r[2],
                    r[3],
                    r[4],
                    r[5],
                    r[6],
                )
            )

    for (
        title,
        year,
        kind,
        imdb,
        rt,
        meta,
        genres,
    ) in GENRE_EXTRA.get(
        genre,
        [],
    ):

        items.append(
            (
                title,
                year,
                kind,
                imdb,
                rt,
                meta,
            )
        )

    seen = set()
    uniq = []

    for item in sorted(
        items,
        key=lambda x: -x[3],
    ):

        if item[0] not in seen:

            seen.add(
                item[0]
            )

            uniq.append(
                item
            )

    uniq = uniq[:25]

    lines = []

    for i, row in enumerate(
        uniq,
        1,
    ):

        lines.append(
            _fmt_entry(
                i,
                *row,
                lang,
            )
        )

    title_line = (
        f"🎭 <b>{clean(genre)}</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
    )

    await call.message.edit_text(
        (
            title_line
            + "\n\n".join(
                lines
            )
        )[:4090],
        reply_markup=genre_kb(
            lang
        ),
    )

    await call.answer()


# ============================================================
# UPCOMING
# ============================================================

@router.callback_query(
    F.data == "menu:upcoming"
)
async def upcoming(
    call: CallbackQuery,
):

    lang = lang_of(
        call.from_user.id
    )

    if TMDB_API_KEY:

        try:

            async with aiohttp.ClientSession() as session:

                url = (
                    "https://api.themoviedb.org/3/movie/upcoming"
                )

                params = {
                    "api_key": TMDB_API_KEY,
                    "language": (
                        "fa-IR"
                        if lang == "fa"
                        else "en-US"
                    ),
                    "page": 1,
                }

                async with session.get(
                    url,
                    params=params,
                    timeout=10,
                ) as response:

                    data = await response.json()

            lines = []

            for movie in data.get(
                "results",
                [],
            )[:15]:

                title = (
                    movie.get("title")
                    or "بدون نام"
                )

                date = (
                    movie.get(
                        "release_date"
                    )
                    or "TBA"
                )

                lines.append(
                    f"🎬 <b>{clean(title)}</b>\n"
                    f"   📅 {date}"
                )

            text = (
                "📅 <b>در انتظار اکران</b>\n"
                "━━━━━━━━━━━━━━━━\n\n"
                + "\n\n".join(
                    lines
                )
            )

            await call.message.edit_text(
                text[:4090],
                reply_markup=back_kb(
                    lang
                ),
            )

            await call.answer()

            return

        except Exception:

            logger.exception(
                "TMDb upcoming failed"
            )

    lines = []

    for title, date, desc in UPCOMING:

        lines.append(
            f"🎬 <b>{clean(title)}</b>\n"
            f"   📅 {date}\n"
            f"   {clean(desc)}"
        )

    text = (
        "📅 <b>در انتظار اکران</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(
            lines
        )
    )

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_kb(
            lang
        ),
    )

    await call.answer()


# ============================================================
# ACTOR
# ============================================================

@router.callback_query(
    F.data == "menu:actor"
)
async def ask_actor(
    call: CallbackQuery,
    state: FSMContext,
):

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        t(
            "ask_actor_name",
            lang,
        ),
        reply_markup=back_kb(
            lang
        ),
    )

    await state.set_state(
        TextSearch.actor
    )

    await call.answer()


@router.message(
    TextSearch.actor
)
async def do_actor_search(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(
        message.from_user.id
    )

    query = (
        message.text or ""
    ).strip()

    result = ACTORS.get(
        query.lower()
    )

    if not result and TMDB_API_KEY:

        try:

            from providers import _tmdb_get

            data = await _tmdb_get(
                "/search/person",
                {
                    "query": query,
                    "language": (
                        "fa-IR"
                        if lang == "fa"
                        else "en-US"
                    ),
                },
            )

            if data and data.get(
                "results"
            ):

                person = data[
                    "results"
                ][0]

                person_id = person[
                    "id"
                ]

                credits = await _tmdb_get(
                    f"/person/{person_id}/combined_credits",
                    {
                        "language": (
                            "fa-IR"
                            if lang == "fa"
                            else "en-US"
                        ),
                    },
                )

                if credits:

                    result = []

                    for item in sorted(
                        credits.get(
                            "cast",
                            []
                        ),
                        key=lambda x: x.get(
                            "popularity",
                            0,
                        ),
                        reverse=True,
                    )[:10]:

                        title = (
                            item.get("title")
                            or item.get("name")
                        )

                        if title:

                            result.append(
                                title
                            )

        except Exception:

            logger.exception(
                "Actor search failed"
            )

    if result:

        lines = []

        for i, item in enumerate(
            result,
            1,
        ):

            lines.append(
                f"{i}. 🎬 {clean(item)}"
            )

        await message.answer(
            (
                f"🎭 <b>{clean(query)}</b>\n"
                "━━━━━━━━━━━━━━━━\n\n"
                + "\n".join(
                    lines
                )
            ),
            reply_markup=back_kb(
                lang
            ),
        )

    else:

        await message.answer(
            "😕 بازیگر موردنظر پیدا نشد.",
            reply_markup=back_kb(
                lang
            ),
        )

    await state.clear()


# ============================================================
# DIRECTOR
# ============================================================

@router.callback_query(
    F.data == "menu:director"
)
async def ask_director(
    call: CallbackQuery,
    state: FSMContext,
):

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        t(
            "ask_director_name",
            lang,
        ),
        reply_markup=back_kb(
            lang
        ),
    )

    await state.set_state(
        TextSearch.director
    )

    await call.answer()


@router.message(
    TextSearch.director
)
async def do_director_search(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(
        message.from_user.id
    )

    query = (
        message.text or ""
    ).strip()

    result = DIRECTORS.get(
        query.lower()
    )

    if not result and TMDB_API_KEY:

        try:

            from providers import _tmdb_get

            data = await _tmdb_get(
                "/search/person",
                {
                    "query": query,
                    "language": (
                        "fa-IR"
                        if lang == "fa"
                        else "en-US"
                    ),
                },
            )

            if data and data.get(
                "results"
            ):

                person_id = data[
                    "results"
                ][0]["id"]

                credits = await _tmdb_get(
                    f"/person/{person_id}/combined_credits",
                    {
                        "language": (
                            "fa-IR"
                            if lang == "fa"
                            else "en-US"
                        ),
                    },
                )

                if credits:

                    result = []

                    for item in sorted(
                        credits.get(
                            "crew",
                            []
                        ),
                        key=lambda x: x.get(
                            "popularity",
                            0,
                        ),
                        reverse=True,
                    )[:10]:

                        title = (
                            item.get("title")
                            or item.get("name")
                        )

                        if title:

                            result.append(
                                title
                            )

        except Exception:

            logger.exception(
                "Director search failed"
            )

    if result:

        lines = []

        for i, item in enumerate(
            result,
            1,
        ):

            lines.append(
                f"{i}. 🎬 {clean(item)}"
            )

        await message.answer(
            (
                f"🎬 <b>{clean(query)}</b>\n"
                "━━━━━━━━━━━━━━━━\n\n"
                + "\n".join(
                    lines
                )
            ),
            reply_markup=back_kb(
                lang
            ),
        )

    else:

        await message.answer(
            "😕 کارگردان موردنظر پیدا نشد.",
            reply_markup=back_kb(
                lang
            ),
        )

    await state.clear()


# ============================================================
# COMPARE
# ============================================================

@router.callback_query(
    F.data == "menu:compare"
)
async def ask_compare(
    call: CallbackQuery,
    state: FSMContext,
):

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        t(
            "ask_movie_name",
            lang,
        ),
        reply_markup=back_kb(
            lang
        ),
    )

    await state.set_state(
        TextSearch.movie
    )

    await call.answer()


@router.message(
    TextSearch.movie
)
async def do_compare(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(
        message.from_user.id
    )

    query = (
        message.text or ""
    ).strip()

    imdb = None
    rt = None
    meta = None

    for r in IMDB_TOP:

        if r[1].lower() == query.lower():

            imdb = r[4]
            rt = r[5]
            meta = r[6]

            break

    if (
        imdb is None
        and rt is None
        and meta is None
        and OMDB_API_KEY
    ):

        try:

            async with aiohttp.ClientSession() as session:

                url = (
                    "https://www.omdbapi.com/"
                )

                params = {
                    "apikey": OMDB_API_KEY,
                    "t": query,
                }

                async with session.get(
                    url,
                    params=params,
                    timeout=10,
                ) as response:

                    data = await response.json()

            if data.get(
                "Response"
            ) == "True":

                for source in data.get(
                    "Ratings",
                    [],
                ):

                    source_name = source.get(
                        "Source"
                    )

                    value = source.get(
                        "Value",
                        "",
                    )

                    if source_name == (
                        "Internet Movie Database"
                    ):

                        imdb = (
                            value.split(
                                "/"
                            )[0]
                        )

                    elif source_name == (
                        "Rotten Tomatoes"
                    ):

                        rt = value.replace(
                            "%",
                            "",
                        )

                    elif source_name == (
                        "Metacritic"
                    ):

                        meta = (
                            value.split(
                                "/"
                            )[0]
                        )

        except Exception:

            logger.exception(
                "OMDb request failed"
            )

    if (
        imdb is None
        and rt is None
        and meta is None
    ):

        text = (
            "😕 <b>عنوان پیدا نشد</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"🔎 {clean(query)}"
        )

    else:

        text = (
            f"🎬 <b>{clean(query)}</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"⭐ IMDb: <b>{imdb or '—'}</b>/10\n"
            f"🍅 Rotten Tomatoes: <b>{rt or '—'}</b>%\n"
            f"Ⓜ️ Metacritic: <b>{meta or '—'}</b>/100"
        )

    await message.answer(
        text,
        reply_markup=back_kb(
            lang
        ),
    )

    await state.clear()


# ============================================================
# RECOMMENDATION QUIZ
# ============================================================

@router.callback_query(
    F.data == "menu:recommend"
)
async def start_quiz(
    call: CallbackQuery,
    state: FSMContext,
):

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        t(
            "start_quiz",
            lang,
        )
    )

    await call.message.answer(
        t(
            "q_mood",
            lang,
        ),
        reply_markup=mood_kb(
            lang
        ),
    )

    await state.set_state(
        Quiz.mood
    )

    await call.answer()


@router.callback_query(
    Quiz.mood,
    F.data.startswith("mood:")
)
async def quiz_mood(
    call: CallbackQuery,
    state: FSMContext,
):

    lang = lang_of(
        call.from_user.id
    )

    await state.update_data(
        mood=call.data.split(
            ":",
            1,
        )[1]
    )

    await call.message.edit_text(
        t(
            "q_genre",
            lang,
        ),
        reply_markup=quiz_genre_kb(
            lang
        ),
    )

    await state.set_state(
        Quiz.genre
    )

    await call.answer()


@router.callback_query(
    Quiz.genre,
    F.data.startswith("qgenre:")
)
async def quiz_genre(
    call: CallbackQuery,
    state: FSMContext,
):

    lang = lang_of(
        call.from_user.id
    )

    await state.update_data(
        genre=call.data.split(
            ":",
            1,
        )[1]
    )

    await call.message.edit_text(
        t(
            "q_mbti",
            lang,
        ),
        reply_markup=mbti_kb(
            lang
        ),
    )

    await state.set_state(
        Quiz.mbti
    )

    await call.answer()


@router.callback_query(
    Quiz.mbti,
    F.data.startswith("mbti:")
)
async def quiz_mbti(
    call: CallbackQuery,
    state: FSMContext,
):

    lang = lang_of(
        call.from_user.id
    )

    await state.update_data(
        mbti=call.data.split(
            ":",
            1,
        )[1]
    )

    await call.message.edit_text(
        t(
            "q_liked",
            lang,
        )
    )

    await state.set_state(
        Quiz.liked
    )

    await call.answer()


@router.message(
    Quiz.liked
)
async def quiz_liked(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(
        message.from_user.id
    )

    text = (
        message.text or ""
    ).strip()

    liked = (
        []
        if text == "-"
        else [
            x.strip()
            for x in text.split(",")
            if x.strip()
        ]
    )

    await state.update_data(
        liked=liked
    )

    await message.answer(
        t(
            "q_disliked",
            lang,
        )
    )

    await state.set_state(
        Quiz.disliked
    )


@router.message(
    Quiz.disliked
)
async def quiz_disliked(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(
        message.from_user.id
    )

    text = (
        message.text or ""
    ).strip()

    disliked = (
        []
        if text == "-"
        else [
            x.strip()
            for x in text.split(",")
            if x.strip()
        ]
    )

    await message.answer(
        t(
            "analyzing",
            lang,
        )
    )

    data = await state.get_data()

    results = recommend(
        genre_pref=data.get(
            "genre"
        ),
        mood=data.get(
            "mood"
        ),
        mbti=data.get(
            "mbti"
        ),
        liked_titles=data.get(
            "liked",
            [],
        ),
        disliked_titles=disliked,
        top_n=6,
    )

    lines = []

    for i, item in enumerate(
        results,
        1,
    ):

        rt_s = (
            f"{item['rt']}%"
            if item["rt"] is not None
            else "—"
        )

        meta_s = (
            f"{item['meta']}"
            if item["meta"] is not None
            else "—"
        )

        lines.append(
            (
                f"{i}. 🎬 <b>{clean(item['title'])}</b> "
                f"({item['year']})\n"
                f"   🎭 {', '.join(item['genres'])}\n"
                f"   ⭐ IMDb {item['imdb']} • "
                f"🍅 RT {rt_s} • "
                f"Ⓜ️ {meta_s}"
            )
        )

    await message.answer(
        t(
            "recommend_header",
            lang,
        )
        + "\n\n"
        + "\n\n".join(
            lines
        ),
        reply_markup=back_kb(
            lang
        ),
    )

    await state.clear()


# ============================================================
# FALLBACK TEXT SEARCH
# ============================================================

@router.message()
async def fallback_text_search(
    message: Message,
):

    text = (
        message.text or ""
    ).strip()

    if not text:
        return

    # جلوگیری از پاسخ به دستورات
    if text.startswith("/"):
        return

    lang = lang_of(
        message.from_user.id
    )

    if not TMDB_API_KEY:

        await message.answer(
            (
                "⚠️ <b>TMDb API تنظیم نشده</b>\n\n"
                "لطفاً TMDB_API_KEY را در "
                "Environment Variables قرار بده."
            )
        )

        return

    await message.answer(
        "🔎 در حال پیدا کردن فیلم و سریال..."
    )

    try:

        results = await search_movies(
            text,
            language=(
                "fa-IR"
                if lang == "fa"
                else "en-US"
            ),
            limit=8,
        )

    except Exception:

        logger.exception(
            "Fallback search failed"
        )

        await message.answer(
            "⚠️ جستجو با مشکل مواجه شد."
        )

        return

    if not results:

        await message.answer(
            (
                "😕 چیزی برای "
                f"<b>{clean(text)}</b> پیدا نشد."
            )
        )

        return

    buttons = []

    for movie in results:

        title = (
            movie.get("title")
            or movie.get("name")
            or "Unknown"
        )

        media_type = movie.get(
            "_media_type",
            "movie",
        )

        tmdb_id = movie.get(
            "id"
        )

        icon = (
            "📺"
            if media_type == "tv"
            else "🎬"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{icon} "
                        f"{title[:45]}"
                    ),
                    callback_data=(
                        f"result:{media_type}:{tmdb_id}"
                    ),
                )
            ]
        )

    await message.answer(
        (
            "🎬 <b>نتایج پیدا شد</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "عنوان موردنظر را انتخاب کن:"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    if (
        not BOT_TOKEN
        or ":" not in BOT_TOKEN
    ):

        raise SystemExit(
            "BOT_TOKEN is missing or invalid."
        )

    if not TMDB_API_KEY:

        logger.warning(
            "TMDB_API_KEY is not configured."
        )

    # ساخت خودکار movies.db
    init_movie_db()

    logger.info(
        "Movie database initialized."
    )

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher(
        storage=MemoryStorage()
    )

    dp.include_router(
        router
    )

    await bot.delete_webhook(
        drop_pending_updates=False
    )

    logger.info(
        "MovieBot started."
    )

    try:

        await dp.start_polling(
            bot,
            allowed_updates=(
                dp.resolve_used_update_types()
            ),
        )

    finally:

        await bot.session.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    keep_alive()

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "MovieBot stopped."
)
