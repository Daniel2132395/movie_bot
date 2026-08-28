import asyncio
import logging
import os
from threading import Thread

import aiohttp
from flask import Flask
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
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


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "").strip()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()


# ============================================================
# FLASK SERVER FOR RENDER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running!", 200


@app.route("/health")
def health():
    return "OK", 200


def run_web_server():
    port = int(os.getenv("PORT", "8080"))

    logger.info("Starting web server on port %s", port)

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
# BOT
# ============================================================

router = Router()

# In-memory language storage.
# This is fine for one running bot process.
USER_LANG: dict[int, str] = {}


def lang_of(uid: int) -> str:
    return USER_LANG.get(uid, "en")


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


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        t("choose_lang", "en"),
        reply_markup=lang_kb(),
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()

    lang = lang_of(message.from_user.id)

    await message.answer(
        t("cancelled", lang)
    )

    await message.answer(
        t("welcome", lang),
        reply_markup=main_menu_kb(lang),
    )


# ============================================================
# LANGUAGE
# ============================================================

@router.callback_query(F.data.startswith("lang:"))
async def set_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":", 1)[1]

    USER_LANG[call.from_user.id] = lang

    await call.message.edit_text(
        t("welcome", lang),
        reply_markup=main_menu_kb(lang),
    )

    await call.answer()


@router.callback_query(F.data == "menu:home")
async def menu_home(call: CallbackQuery, state: FSMContext):
    await state.clear()

    lang = lang_of(call.from_user.id)

    await call.message.edit_text(
        t("welcome", lang),
        reply_markup=main_menu_kb(lang),
    )

    await call.answer()


@router.callback_query(F.data == "menu:lang")
async def menu_lang(call: CallbackQuery):
    lang = lang_of(call.from_user.id)

    await call.message.edit_text(
        t("choose_lang", lang),
        reply_markup=lang_kb(),
    )

    await call.answer()


# ============================================================
# TOP IMDb
# ============================================================

def _fmt_entry(idx, title, year, kind, imdb, rt, meta, lang):
    if kind == "series":
        kind_label = "سریال" if lang == "fa" else "Series"
    else:
        kind_label = "فیلم" if lang == "fa" else "Movie"

    rt_s = f"{rt}%" if rt is not None else "—"
    meta_s = f"{meta}" if meta is not None else "—"

    return (
        f"{idx}. <b>{title}</b> ({year}) [{kind_label}]\n"
        f"    IMDb: {imdb} | RT: {rt_s} | Metacritic: {meta_s}"
    )


@router.callback_query(F.data == "menu:top250")
async def top250(call: CallbackQuery):
    lang = lang_of(call.from_user.id)

    sorted_list = sorted(
        IMDB_TOP,
        key=lambda r: -r[4],
    )

    lines = [
        _fmt_entry(
            i + 1,
            r[1],
            r[2],
            r[3],
            r[4],
            r[5],
            r[6],
            lang,
        )
        for i, r in enumerate(sorted_list[:40])
    ]

    if lang == "fa":
        header = (
            "🏆 <b>برترین‌های امتیاز IMDb</b> "
            "(نسخه فشرده — ۴۰ مورد اول از دیتاست داخلی)\n\n"
        )

        footer = (
            "\n\nℹ️ برای فهرست کامل و همیشه به‌روز "
            "۲۵۰ تایی، کلید رایگان OMDb/TMDb را در .env قرار دهید."
        )

    else:
        header = (
            "🏆 <b>Top IMDb-rated titles</b> "
            "(showing top 40 of the bundled dataset)\n\n"
        )

        footer = (
            "\n\nℹ️ For the complete, always-current "
            "250-title list, add a free OMDb/TMDb key in .env."
        )

    text = header + "\n\n".join(lines) + footer

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_kb(lang),
    )

    await call.answer()


# ============================================================
# GENRES
# ============================================================

@router.callback_query(F.data == "menu:genre")
async def menu_genre(call: CallbackQuery):
    lang = lang_of(call.from_user.id)

    await call.message.edit_text(
        t("pick_genre", lang),
        reply_markup=genre_kb(lang),
    )

    await call.answer()


@router.callback_query(F.data.startswith("genre:"))
async def show_genre(call: CallbackQuery):
    lang = lang_of(call.from_user.id)

    genre = call.data.split(":", 1)[1]

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

    for title, year, kind, imdb, rt, meta, genres in GENRE_EXTRA.get(
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
            seen.add(item[0])
            uniq.append(item)

    uniq = uniq[:25]

    lines = [
        _fmt_entry(
            i + 1,
            *row,
            lang,
        )
        for i, row in enumerate(uniq)
    ]

    if lang == "en":
        title_line = (
            f"🎬 <b>{genre}</b> — Top picks\n\n"
        )
    else:
        title_line = (
            f"🎬 <b>{genre}</b> — برترین‌ها\n\n"
        )

    await call.message.edit_text(
        (title_line + "\n\n".join(lines))[:4090],
        reply_markup=genre_kb(lang),
    )

    await call.answer()


# ============================================================
# UPCOMING
# ============================================================

@router.callback_query(F.data == "menu:upcoming")
async def upcoming(call: CallbackQuery):
    lang = lang_of(call.from_user.id)

    if TMDB_API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                url = (
                    "https://api.themoviedb.org/3/movie/upcoming"
                    f"?api_key={TMDB_API_KEY}"
                    f"&language={'fa' if lang == 'fa' else 'en'}-US"
                )

                async with session.get(
                    url,
                    timeout=10,
                ) as response:
                    data = await response.json()

            lines = []

            for movie in data.get("results", [])[:15]:
                lines.append(
                    f"🎬 <b>{movie.get('title')}</b> — "
                    f"{movie.get('release_date', 'TBA')}"
                )

            if lang == "fa":
                header = (
                    "📅 <b>در انتظار اکران "
                    "(زنده از TMDb)</b>\n\n"
                )
            else:
                header = (
                    "📅 <b>Upcoming releases "
                    "(live from TMDb)</b>\n\n"
                )

            await call.message.edit_text(
                (header + "\n".join(lines))[:4090],
                reply_markup=back_kb(lang),
            )

            await call.answer()

            return

        except Exception:
            logger.exception(
                "TMDB upcoming request failed"
            )

    if lang == "fa":
        header = (
            "📅 <b>در انتظار اکران "
            "(فهرست ثابت)</b>\n\n"
        )
    else:
        header = (
            "📅 <b>Most anticipated upcoming "
            "(static list)</b>\n\n"
        )

    lines = [
        f"🎬 <b>{title}</b> — {date}\n    {desc}"
        for title, date, desc in UPCOMING
    ]

    if lang == "fa":
        footer = (
            "\n\nℹ️ برای فهرست زنده و همیشه به‌روز، "
            "TMDB_API_KEY را در .env تنظیم کنید."
        )
    else:
        footer = (
            "\n\nℹ️ For a live, always-fresh list, "
            "set TMDB_API_KEY in .env."
        )

    await call.message.edit_text(
        (
            header
            + "\n\n".join(lines)
            + footer
        )[:4090],
        reply_markup=back_kb(lang),
    )

    await call.answer()


# ============================================================
# TMDB PERSON SEARCH
# ============================================================

async def _tmdb_person_credits(
    name: str,
    lang: str,
):
    if not TMDB_API_KEY:
        return None

    async with aiohttp.ClientSession() as session:

        search_url = (
            "https://api.themoviedb.org/3/search/person"
            f"?api_key={TMDB_API_KEY}"
            f"&query={name}"
        )

        async with session.get(
            search_url,
            timeout=10,
        ) as response:
            data = await response.json()

        results = data.get("results", [])

        if not results:
            return None

        person_id = results[0]["id"]

        credits_url = (
            f"https://api.themoviedb.org/3/person/"
            f"{person_id}/movie_credits"
            f"?api_key={TMDB_API_KEY}"
        )

        async with session.get(
            credits_url,
            timeout=10,
        ) as response:
            credits = await response.json()

        cast = sorted(
            credits.get("cast", [])
            + credits.get("crew", []),
            key=lambda movie: movie.get(
                "popularity",
                0,
            ),
            reverse=True,
        )

        return [
            (
                f"{movie.get('title')} "
                f"({(movie.get('release_date') or 'TBA')[:4]})"
            )
            for movie in cast[:10]
        ]


# ============================================================
# ACTOR
# ============================================================

@router.callback_query(F.data == "menu:actor")
async def ask_actor(
    call: CallbackQuery,
    state: FSMContext,
):
    lang = lang_of(call.from_user.id)

    await call.message.edit_text(
        t("ask_actor_name", lang),
        reply_markup=back_kb(lang),
    )

    await state.set_state(TextSearch.actor)

    await call.answer()


@router.message(TextSearch.actor)
async def do_actor_search(
    message: Message,
    state: FSMContext,
):
    lang = lang_of(message.from_user.id)

    name = message.text.strip().lower()

    result = ACTORS.get(name)

    if not result and TMDB_API_KEY:
        result = await _tmdb_person_credits(
            message.text.strip(),
            lang,
        )

    if result:
        title = (
            f"🎭 <b>{message.text.strip()}</b> — Top 10:\n\n"
        )

        await message.answer(
            title
            + "\n".join(
                f"{i + 1}. {x}"
                for i, x in enumerate(result)
            ),
            reply_markup=back_kb(lang),
        )

    else:
        await message.answer(
            t("not_found_local", lang),
            reply_markup=back_kb(lang),
        )

    await state.clear()


# ============================================================
# DIRECTOR
# ============================================================

@router.callback_query(F.data == "menu:director")
async def ask_director(
    call: CallbackQuery,
    state: FSMContext,
):
    lang = lang_of(call.from_user.id)

    await call.message.edit_text(
        t("ask_director_name", lang),
        reply_markup=back_kb(lang),
    )

    await state.set_state(TextSearch.director)

    await call.answer()


@router.message(TextSearch.director)
async def do_director_search(
    message: Message,
    state: FSMContext,
):
    lang = lang_of(message.from_user.id)

    name = message.text.strip().lower()

    result = DIRECTORS.get(name)

    if not result and TMDB_API_KEY:
        result = await _tmdb_person_credits(
            message.text.strip(),
            lang,
        )

    if result:
        title = (
            f"🎬 <b>{message.text.strip()}</b> — Top 10:\n\n"
        )

        await message.answer(
            title
            + "\n".join(
                f"{i + 1}. {x}"
                for i, x in enumerate(result)
            ),
            reply_markup=back_kb(lang),
        )

    else:
        await message.answer(
            t("not_found_local", lang),
            reply_markup=back_kb(lang),
        )

    await state.clear()


# ============================================================
# COMPARE
# ============================================================

@router.callback_query(F.data == "menu:compare")
async def ask_compare(
    call: CallbackQuery,
    state: FSMContext,
):
    lang = lang_of(call.from_user.id)

    await call.message.edit_text(
        t("ask_movie_name", lang),
        reply_markup=back_kb(lang),
    )

    await state.set_state(TextSearch.movie)

    await call.answer()


@router.message(TextSearch.movie)
async def do_compare(
    message: Message,
    state: FSMContext,
):
    lang = lang_of(message.from_user.id)

    query = message.text.strip()

    imdb = None
    rt = None
    meta = None

    found_locally = False

    for r in IMDB_TOP:
        if r[1].lower() == query.lower():
            imdb = r[4]
            rt = r[5]
            meta = r[6]

            found_locally = True
            break

    if not found_locally and OMDB_API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                url = (
                    "http://www.omdbapi.com/"
                    f"?apikey={OMDB_API_KEY}"
                    f"&t={query}"
                )

                async with session.get(
                    url,
                    timeout=10,
                ) as response:
                    data = await response.json()

            if data.get("Response") == "True":

                for source in data.get(
                    "Ratings",
                    [],
                ):
                    if source["Source"] == "Internet Movie Database":
                        imdb = source["Value"].split("/")[0]

                    elif source["Source"] == "Rotten Tomatoes":
                        rt = source["Value"].replace(
                            "%",
                            "",
                        )

                    elif source["Source"] == "Metacritic":
                        meta = source["Value"].split("/")[0]

        except Exception:
            logger.exception(
                "OMDb request failed"
            )

    header = t(
        "compare_header",
        lang,
        title=query,
    )

    if imdb is None and rt is None and meta is None:

        await message.answer(
            header
            + t("not_found_local", lang),
            reply_markup=back_kb(lang),
        )

    else:

        body = (
            f"⭐ IMDb: <b>{imdb or '—'}</b>/10\n"
            f"🍅 Rotten Tomatoes: <b>{rt or '—'}</b>%\n"
            f"🅼 Metacritic: <b>{meta or '—'}</b>/100"
        )

        await message.answer(
            header + body,
            reply_markup=back_kb(lang),
        )

    await state.clear()


# ============================================================
# SMART RECOMMENDATION QUIZ
# ============================================================

@router.callback_query(F.data == "menu:recommend")
async def start_quiz(
    call: CallbackQuery,
    state: FSMContext,
):
    lang = lang_of(call.from_user.id)

    await call.message.edit_text(
        t("start_quiz", lang)
    )

    await call.message.answer(
        t("q_mood", lang),
        reply_markup=mood_kb(lang),
    )

    await state.set_state(Quiz.mood)

    await call.answer()


@router.callback_query(
    Quiz.mood,
    F.data.startswith("mood:")
)
async def quiz_mood(
    call: CallbackQuery,
    state: FSMContext,
):
    lang = lang_of(call.from_user.id)

    await state.update_data(
        mood=call.data.split(":", 1)[1]
    )

    await call.message.edit_text(
        t("q_genre", lang),
        reply_markup=quiz_genre_kb(lang),
    )

    await state.set_state(Quiz.genre)

    await call.answer()


@router.callback_query(
    Quiz.genre,
    F.data.startswith("qgenre:")
)
async def quiz_genre(
    call: CallbackQuery,
    state: FSMContext,
):
    lang = lang_of(call.from_user.id)

    await state.update_data(
        genre=call.data.split(":", 1)[1]
    )

    await call.message.edit_text(
        t("q_mbti", lang),
        reply_markup=mbti_kb(lang),
    )

    await state.set_state(Quiz.mbti)

    await call.answer()


@router.callback_query(
    Quiz.mbti,
    F.data.startswith("mbti:")
)
async def quiz_mbti(
    call: CallbackQuery,
    state: FSMContext,
):
    lang = lang_of(call.from_user.id)

    await state.update_data(
        mbti=call.data.split(":", 1)[1]
    )

    await call.message.edit_text(
        t("q_liked", lang)
    )

    await state.set_state(Quiz.liked)

    await call.answer()


@router.message(Quiz.liked)
async def quiz_liked(
    message: Message,
    state: FSMContext,
):
    lang = lang_of(message.from_user.id)

    text = message.text.strip()

    liked = (
        []
        if text == "-"
        else [
            x.strip()
            for x in text.split(",")
        ]
    )

    await state.update_data(
        liked=liked
    )

    await message.answer(
        t("q_disliked", lang)
    )

    await state.set_state(
        Quiz.disliked
    )


@router.message(Quiz.disliked)
async def quiz_disliked(
    message: Message,
    state: FSMContext,
):
    lang = lang_of(message.from_user.id)

    text = message.text.strip()

    disliked = (
        []
        if text == "-"
        else [
            x.strip()
            for x in text.split(",")
        ]
    )

    await message.answer(
        t("analyzing", lang)
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
            f"{item['meta']}"
            if item["meta"] is not None
            else "—"
        )

        lines.append(
            f"{i}. <b>{item['title']}</b> "
            f"({item['year']})\n"
            f"    {', '.join(item['genres'])}\n"
            f"    IMDb {item['imdb']} | "
            f"RT {rt_s} | "
            f"Metacritic {meta_s}"
        )

    await message.answer(
        t("recommend_header", lang)
        + "\n\n"
        + "\n\n".join(lines),
        reply_markup=back_kb(lang),
    )

    await state.clear()


# ============================================================
# MAIN
# ============================================================

async def main():

    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN is missing/invalid. "
            "Set BOT_TOKEN in Render Environment Variables."
        )

    logger.info("Starting bot...")

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher(
        storage=MemoryStorage()
    )

    dp.include_router(router)

    # Remove webhook so polling can work.
    # Do NOT delete pending updates.
    await bot.delete_webhook(
        drop_pending_updates=False
    )

    logger.info(
        "Starting Telegram polling..."
    )

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    finally:
        await bot.session.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    # Start Flask health server first.
    keep_alive()

    # Start Telegram polling.
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info(
            "Bot stopped manually."
      )
