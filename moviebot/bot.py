# bot.py
# ============================================================
# MovieBot
# aiogram 3.x + SQLite
#
# جستجوی فیلم:
#   فقط از providers.py
#   بدون TMDb
#
# لینک مستقیم ویدئو:
#   ندارد
#
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
    get_provider_results,
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


def language_code(user_id: int) -> str:
    return (
        "fa-IR"
        if lang_of(user_id) == "fa"
        else "en-US"
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

    if lang not in (
        "fa",
        "en",
    ):

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
            "منطقه موردنظر را انتخاب کن.\n\n"
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

    lang = lang_of(
        call.from_user.id
    )

    await call.message.edit_text(
        (
            "✅ <b>منطقه ذخیره شد</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"🌍 منطقه: <b>{region}</b>"
        ),
        reply_markup=main_menu_kb(lang),
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
    region = region_of(user_id)

    await call.message.edit_text(
        (
            "🎬 <b>جستجو و تماشای فیلم</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "🔎 فیلم یا سریالت را جستجو کن.\n\n"
            "جستجو مستقیماً از سرویس‌های تعریف‌شده "
            "در providers.py انجام می‌شود.\n\n"
            f"🌍 منطقه: <b>{region}</b>\n\n"
            "👇 یکی از گزینه‌ها را انتخاب کن:"
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
            "نام فیلم یا سریال را بفرست.\n\n"
            "مثلاً:\n"
            "🎬 Interstellar\n"
            "📺 Breaking Bad\n"
            "🎬 Inception"
        ),
        reply_markup=search_watch_kb(lang),
    )

    await state.set_state(
        MovieSearch.query
    )

    await call.answer()


# ============================================================
# PROVIDER MOVIE SEARCH
# ============================================================

async def perform_movie_search(
    query: str,
    user_id: int,
):

    return await search_movies(
        query,
        language=language_code(user_id),
        limit=10,
    )


# ============================================================
# MOVIE SEARCH
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
            "❌ لطفاً نام فیلم یا سریال را ارسال کن."
        )

        return

    loading = await message.answer(
        (
            "🔎 <b>در حال جستجو...</b>\n\n"
            f"🎬 <code>{clean(query)}</code>\n"
            "🇮🇷 در سرویس‌های ایرانی..."
        )
    )

    try:

        results = await perform_movie_search(
            query,
            message.from_user.id,
        )

    except Exception:

        logger.exception(
            "Iranian provider search failed"
        )

        await loading.edit_text(
            (
                "⚠️ <b>خطا در جستجو</b>\n\n"
                "یکی از سرویس‌ها موقتاً در دسترس نیست."
            ),
            reply_markup=search_watch_kb(
                lang_of(
                    message.from_user.id
                )
            ),
        )

        await state.clear()

        return

    await state.clear()

    if not results:

        await loading.edit_text(
            (
                "😕 <b>نتیجه‌ای پیدا نشد</b>\n"
                "━━━━━━━━━━━━━━━━\n\n"
                f"🔎 جستجو: <b>{clean(query)}</b>\n\n"
                "نام دیگری را امتحان کن."
            ),
            reply_markup=search_watch_kb(
                lang_of(
                    message.from_user.id
                )
            ),
        )

        return

    await loading.edit_text(
        (
            "🎬 <b>نتایج جستجو</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"🔎 «{clean(query)}»\n\n"
            "برای ورود به جستجوی هر سرویس، "
            "گزینه موردنظر را انتخاب کن:"
        ),
        reply_markup=search_results_kb(
            results
        ),
    )


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

    provider_key = parts[1]

    query = parts[2]

    if not provider_key or not query:

        await call.answer(
            "اطلاعات ناقص است.",
            show_alert=True,
        )

        return

    # query داخل callback-data با + یا درصدکد ارسال می‌شود.
    from urllib.parse import unquote_plus

    try:
        decoded_query = unquote_plus(query)
    except Exception:
        decoded_query = query

    await call.answer(
        "🔎 در حال آماده‌سازی..."
    )

    providers = await get_provider_results(
        decoded_query
    )

    selected = None

    for item in providers:

        if item.get("id") == provider_key:

            selected = item
            break

    if not selected:

        await call.message.edit_text(
            (
                "😕 <b>سرویس پیدا نشد</b>\n"
                "━━━━━━━━━━━━━━━━\n\n"
                "لطفاً دوباره جستجو کن."
            ),
            reply_markup=search_watch_kb(
                lang_of(
                    call.from_user.id
                )
            ),
        )

        return

    movie = {
        "title": decoded_query,
        "original_title": decoded_query,
        "name": decoded_query,
        "provider_name": selected.get(
            "name",
            "سرویس",
        ),
        "provider_id": selected.get(
            "id"
        ),
        "provider_url": selected.get(
            "url"
        ),
        "overview": (
            f"صفحه جستجوی «{decoded_query}» "
            f"در {selected.get('name', 'سرویس')}."
        ),
        "_media_type": "movie",
    }

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
            provider_id=selected.get(
                "id"
            ),
            provider_url=selected.get(
                "url"
            ),
            query=decoded_query,
        ),
    )


# ============================================================
# PROVIDER WATCH PAGE
# ============================================================

@router.callback_query(
    F.data.startswith("watch:")
)
async def watch_providers(
    call: CallbackQuery,
):

    parts = call.data.split(
        ":",
        2,
    )

    if len(parts) != 3:

        await call.answer(
            "اطلاعات نامعتبر است.",
            show_alert=True,
        )

        return

    provider_key = parts[1]
    query = parts[2]

    from urllib.parse import unquote_plus

    query = unquote_plus(query)

    providers = await get_provider_results(
        query
    )

    selected = None

    for item in providers:

        if item.get("id") == provider_key:

            selected = item
            break

    if not selected:

        await call.answer(
            "سرویس پیدا نشد.",
            show_alert=True,
        )

        return

    text = (
        "📺 <b>سرویس انتخاب‌شده</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"🎬 عنوان: <b>{clean(query)}</b>\n"
        f"🇮🇷 سرویس: <b>{clean(selected.get('name'))}</b>\n\n"
        "برای ادامه، وارد صفحه رسمی جستجوی سرویس شو."
    )

    await call.message.edit_text(
        text,
        reply_markup=watch_kb(
            provider_url=selected.get(
                "url"
            ),
            provider_key=provider_key,
            query=query,
        ),
    )

    await call.answer()


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

    if lang == "fa":

        kind_label = (
            "سریال"
            if kind == "series"
            else "فیلم"
        )

    else:

        kind_label = (
            "Series"
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
        "💡 برای جستجوی عنوان، از بخش "
        "«جستجو و تماشای فیلم» استفاده کن."
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

        items.append(
            (
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
                item[5],
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

    lines = []

    for title, date, desc in UPCOMING:

        lines.append(
            f"🎬 <b>{clean(title)}</b>\n"
            f"   📅 {clean(date)}\n"
            f"   {clean(desc)}"
        )

    if not lines:

        text = (
            "📅 <b>در انتظار اکران</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "اطلاعاتی ثبت نشده است."
        )

    else:

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
            (
                "😕 <b>بازیگر موردنظر پیدا نشد.</b>\n\n"
                "این بخش از داده‌های محلی پروژه استفاده می‌کند."
            ),
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
            (
                "😕 <b>کارگردان موردنظر پیدا نشد.</b>\n\n"
                "این بخش از داده‌های محلی پروژه استفاده می‌کند."
            ),
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
    ):

        text = (
            "😕 <b>عنوان در داده‌های مقایسه پیدا نشد.</b>\n"
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
            lang_of(
                message.from_user.id
            ),
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

    if not results:

        await message.answer(
            "😕 پیشنهادی پیدا نشد.",
            reply_markup=back_kb(lang),
        )

        await state.clear()

        return

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

    await message.answer(
        "🔎 <b>در حال جستجو در سرویس‌های ایرانی...</b>"
    )

    try:

        results = await search_movies(
            text,
            language=language_code(
                message.from_user.id
            ),
            limit=10,
        )

    except Exception:

        logger.exception(
            "Fallback provider search failed"
        )

        await message.answer(
            "⚠️ جستجو با مشکل مواجه شد."
        )

        return

    if not results:

        await message.answer(
            (
                "😕 <b>نتیجه‌ای پیدا نشد.</b>\n\n"
                f"🔎 {clean(text)}"
            ),
            reply_markup=search_watch_kb(
                lang_of(
                    message.from_user.id
                )
            ),
        )

        return

    await message.answer(
        (
            "🎬 <b>نتایج جستجو</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"🔎 «{clean(text)}»\n\n"
            "👇 سرویس موردنظر را انتخاب کن:"
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
