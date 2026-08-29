# bot.py
# ============================================================
# MovieBot
# aiogram 3.x + TMDb + SQLite
# ============================================================

import asyncio
import logging
import os
from html import escape
from threading import Thread

import aiohttp
from flask import Flask
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message

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
    search_watch_kb,
    search_results_kb,
    movie_result_kb,
    watch_kb,
    region_kb,
)

from locales import t
from recommender import recommend

from movie_db import (
    init_movie_db,
    save_movie,
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

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    "",
).strip()

OMDB_API_KEY = os.getenv(
    "OMDB_API_KEY",
    "",
).strip()

DEFAULT_REGION = os.getenv(
    "WATCH_REGION",
    "IR",
).strip().upper()


# ============================================================
# FLASK HEALTH SERVER
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
        "Health server running on port %s",
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
# USER SETTINGS
# ============================================================

USER_LANG: dict[int, str] = {}
USER_REGION: dict[int, str] = {}


def lang_of(user_id: int) -> str:
    return USER_LANG.get(
        user_id,
        "fa",
    )


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
# HELPERS
# ============================================================

def clean(text) -> str:
    if text is None:
        return ""

    return escape(
        str(text)
    )


def language_code(user_id: int) -> str:
    return (
        "fa-IR"
        if lang_of(user_id) == "fa"
        else "en-US"
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

    USER_LANG.setdefault(
        user_id,
        "fa",
    )

    USER_REGION.setdefault(
        user_id,
        DEFAULT_REGION,
    )

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
        ),
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

    if lang not in ("fa", "en"):
        await call.answer(
            "Language error",
            show_alert=True,
        )
        return

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
# REGION
# ============================================================

@router.callback_query(
    F.data == "menu:region"
)
async def choose_region(
    call: CallbackQuery,
):

    region = region_of(
        call.from_user.id
    )

    await call.message.edit_text(
        (
            "🌍 <b>منطقه تماشا</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "کشور را انتخاب کن تا سرویس‌های "
            "قانونی ثبت‌شده برای همان منطقه "
            "بررسی شوند.\n\n"
            f"📍 منطقه فعلی: <b>{region}</b>"
        ),
        reply_markup=region_kb(),
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

    allowed = {
        "IR",
        "GB",
        "US",
        "CA",
    }

    if region not in allowed:
        await call.answer(
            "منطقه نامعتبر است.",
            show_alert=True,
        )
        return

    USER_REGION[
        call.from_user.id
    ] = region

    await call.message.edit_text(
        (
            "✅ <b>منطقه ذخیره شد</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"🌍 منطقه: <b>{region}</b>\n\n"
            "گزینه‌های تماشا از این به بعد "
            "بر اساس این منطقه بررسی می‌شوند."
        ),
        reply_markup=main_menu_kb(
            lang_of(call.from_user.id)
        ),
    )

    await call.answer(
        "ذخیره شد ✅"
    )


# ============================================================
# SEARCH & WATCH CENTER
# ============================================================

@router.callback_query(
    F.data == "menu:search_watch"
)
async def search_watch_center(
    call: CallbackQuery,
):

    user_id = call.from_user.id

    region = region_of(
        user_id
    )

    await call.message.edit_text(
        (
            "🎬 <b>جستجو و تماشای فیلم</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "🔎 فیلم یا سریال موردنظرت را پیدا کن.\n\n"
            "بعد از انتخاب عنوان، اطلاعات آن "
            "و سرویس‌های قانونی قابل دسترس "
            "نمایش داده می‌شوند.\n\n"
            f"🌍 منطقه: <b>{region}</b>\n\n"
            "👇 شروع کن:"
        ),
        reply_markup=search_watch_kb(
            lang_of(user_id)
        ),
    )

    await call.answer()


# ============================================================
# START SEARCH
# ============================================================

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
            "🔎 <b>جستجوی فیلم و سریال</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "نام فیلم یا سریال را ارسال کن.\n\n"
            "مثلاً:\n"
            "🎬 Interstellar\n"
            "📺 Breaking Bad"
        ),
        reply_markup=search_watch_kb(lang),
    )

    await state.set_state(
        MovieSearch.query
    )

    await call.answer()


# ============================================================
# MOVIE SEARCH
# ============================================================

async def perform_movie_search(
    query: str,
    user_id: int,
):

    return await search_movies(
        query,
        language=language_code(user_id),
        limit=8,
    )


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
            "❌ لطفاً نام فیلم یا سریال را ارسال کن."
        )

        return

    await message.answer(
        (
            "🔎 <b>در حال جستجو...</b>\n\n"
            "🎬 دارم بین نتایج TMDb می‌گردم..."
        )
    )

    try:

        results = await perform_movie_search(
            query,
            message.from_user.id,
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
                "😕 <b>نتیجه‌ای پیدا نشد</b>\n"
                "━━━━━━━━━━━━━━━━\n\n"
                f"🔎 جستجو: <b>{clean(query)}</b>\n\n"
                "نام دیگری را امتحان کن."
            ),
            reply_markup=search_watch_kb(
                lang_of(message.from_user.id)
            ),
        )

        await state.clear()

        return

    await message.answer(
        (
            "🎬 <b>نتایج جستجو</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"🔎 «{clean(query)}»\n\n"
            "👇 عنوان موردنظر را انتخاب کن:"
        ),
        reply_markup=search_results_kb(
            results
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

    if media_type not in (
        "movie",
        "tv",
    ):

        await call.answer(
            "نوع عنوان نامعتبر است.",
            show_alert=True,
        )

        return

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

    await call.answer(
        "🎬 در حال دریافت اطلاعات..."
    )

    movie = None

    try:

        from providers import _tmdb_get

        movie = await _tmdb_get(
            f"/{media_type}/{tmdb_id}",
            {
                "language": language_code(
                    call.from_user.id
                )
            },
        )

    except Exception:

        logger.exception(
            "Could not get movie details"
        )

    if not movie:

        await call.message.edit_text(
            (
                "😕 <b>اطلاعات پیدا نشد</b>\n"
                "━━━━━━━━━━━━━━━━\n\n"
                "لطفاً دوباره جستجو کن."
            ),
            reply_markup=search_watch_kb(
                lang_of(call.from_user.id)
            ),
        )

        return

    movie["_media_type"] = media_type

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
        reply_markup=movie_result_kb(
            tmdb_id,
            media_type,
        ),
    )


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

        await call.message.edit_text(
            (
                "⚠️ <b>خطا در دریافت سرویس‌ها</b>\n\n"
                "لطفاً چند لحظه بعد دوباره امتحان کن."
            ),
            reply_markup=movie_result_kb(
                tmdb_id,
                media_type,
            ),
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

        provider_link = None

    else:

        text = (
            "📺 <b>گزینه‌های تماشا</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            + providers_text(
                providers
            )
            + "\n\n"
            "ℹ️ این اطلاعات از بخش Watch Providers "
            "در TMDb دریافت شده است."
        )

        provider_link = providers.get(
            "link"
        )

    await call.message.edit_text(
        text[:4090],
        reply_markup=watch_kb(
            media_type=media_type,
            tmdb_id=tmdb_id,
            provider_link=provider_link,
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

    kind_label = (
        "سریال"
        if kind == "series" and lang == "fa"
        else "فیلم"
        if lang == "fa"
        else "Series"
        if kind == "series"
        else "Movie"
    )

    rt_s = (
        f"{rt}%"
        if rt is not None
        else "—"
    )

    meta_s = (
        str(meta)
        if meta is not None
        else "—"
    )

    return (
        f"{idx}. 🎬 <b>{clean(title)}</b> "
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
        + "\n\n".join(lines)
        + "\n\n"
        "💡 برای مشاهده گزینه‌های قانونی تماشا، "
        "عنوان را از بخش جستجو پیدا کن."
    )

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_kb(lang),
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
        reply_markup=genre_kb(lang),
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

    for item in GENRE_EXTRA.get(
        genre,
        [],
    ):

        title = item[0]
        year = item[1]
        kind = item[2]
        imdb = item[3]
        rt = item[4]
        meta = item[5]

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

    lines = []

    for i, row in enumerate(
        uniq[:25],
        1,
    ):

        lines.append(
            _fmt_entry(
                i,
                *row,
                lang,
            )
        )

    text = (
        f"🎭 <b>{clean(genre)}</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(lines)
    )

    await call.message.edit_text(
        text[:4090],
        reply_markup=genre_kb(lang),
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
                    "language": language_code(
                        call.from_user.id
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
                    f"   📅 {clean(date)}"
                )

            if lines:

                text = (
                    "📅 <b>در انتظار اکران</b>\n"
                    "━━━━━━━━━━━━━━━━\n\n"
                    + "\n\n".join(lines)
                )

                await call.message.edit_text(
                    text[:4090],
                    reply_markup=back_kb(lang),
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
            f"   📅 {clean(date)}\n"
            f"   {clean(desc)}"
        )

    text = (
        "📅 <b>در انتظار اکران</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(lines)
    )

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_kb(lang),
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
        reply_markup=back_kb(lang),
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

    query = (
        message.text or ""
    ).strip()

    lang = lang_of(
        message.from_user.id
    )

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
                    "language": language_code(
                        message.from_user.id
                    ),
                },
            )

            if data and data.get("results"):

                person = data["results"][0]

                credits = await _tmdb_get(
                    f"/person/{person['id']}/combined_credits",
                    {
                        "language": language_code(
                            message.from_user.id
                        ),
                    },
                )

                if credits:

                    result = []

                    for item in sorted(
                        credits.get("cast", []),
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
                            result.append(title)

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
                + "\n".join(lines)
            ),
            reply_markup=back_kb(lang),
        )

    else:

        await message.answer(
            "😕 بازیگر موردنظر پیدا نشد.",
            reply_markup=back_kb(lang),
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
        reply_markup=back_kb(lang),
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

    query = (
        message.text or ""
    ).strip()

    lang = lang_of(
        message.from_user.id
    )

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
                    "language": language_code(
                        message.from_user.id
                    ),
                },
            )

            if data and data.get("results"):

                person_id = data[
                    "results"
                ][0]["id"]

                credits = await _tmdb_get(
                    f"/person/{person_id}/combined_credits",
                    {
                        "language": language_code(
                            message.from_user.id
                        ),
                    },
                )

                if credits:

                    result = []

                    for item in sorted(
                        credits.get(
                            "crew",
                            [],
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
                            result.append(title)

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
                + "\n".join(lines)
            ),
            reply_markup=back_kb(lang),
        )

    else:

        await message.answer(
            "😕 کارگردان موردنظر پیدا نشد.",
            reply_markup=back_kb(lang),
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
        reply_markup=back_kb(lang),
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

    query = (
        message.text or ""
    ).strip()

    lang = lang_of(
        message.from_user.id
    )

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

                async with session.get(
                    "https://www.omdbapi.com/",
                    params={
                        "apikey": OMDB_API_KEY,
                        "t": query,
                    },
                    timeout=10,
                ) as response:

                    data = await response.json()

            if data.get("Response") == "True":

                for source in data.get(
                    "Ratings",
                    [],
                ):

                    name = source.get(
                        "Source"
                    )

                    value = source.get(
                        "Value",
                        "",
                    )

                    if name == "Internet Movie Database":
                        imdb = value.split("/")[0]

                    elif name == "Rotten Tomatoes":
                        rt = value.replace("%", "")

                    elif name == "Metacritic":
                        meta = value.split("/")[0]

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
        reply_markup=back_kb(lang),
    )

    await state.clear()


# ============================================================
# RECOMMENDATION
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
            "q_mood",
            lang,
        ),
        reply_markup=mood_kb(lang),
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
        reply_markup=quiz_genre_kb(lang),
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
        reply_markup=mbti_kb(lang),
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
            lang_of(message.from_user.id),
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
        genre_pref=data.get("genre"),
        mood=data.get("mood"),
        mbti=data.get("mbti"),
        liked_titles=data.get("liked", []),
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
            str(item["meta"])
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
        + "\n\n".join(lines),
        reply_markup=back_kb(lang),
    )

    await state.clear()


# ============================================================
# FALLBACK SEARCH
# ============================================================

@router.message()
async def fallback_text_search(
    message: Message,
):

    text = (
        message.text or ""
    ).strip()

    if not text or text.startswith("/"):
        return

    if not TMDB_API_KEY:

        await message.answer(
            (
                "⚠️ <b>TMDb API تنظیم نشده</b>\n\n"
                "متغیر <code>TMDB_API_KEY</code> "
                "را در Environment Variables قرار بده."
            )
        )

        return

    await message.answer(
        "🔎 <b>در حال جستجو...</b>"
    )

    try:

        results = await perform_movie_search(
            text,
            message.from_user.id,
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

    await message.answer(
        (
            "🎬 <b>نتایج پیدا شد</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "👇 عنوان موردنظر را انتخاب کن:"
        ),
        reply_markup=search_results_kb(
            results
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

    try:

        init_movie_db()

        logger.info(
            "Movie database initialized."
        )

    except Exception:

        logger.exception(
            "Could not initialize movie database"
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
