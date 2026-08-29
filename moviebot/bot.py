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

from movie_db import init_movie_db

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
    return "MovieBot is running!", 200


@app.route("/health")
def health():
    return "OK", 200


def run_web_server():
    port = int(os.getenv("PORT", "8080"))

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
# BOT / ROUTER
# ============================================================

router = Router()


# ============================================================
# USER LANGUAGE
# ============================================================

USER_LANG: dict[int, str] = {}


def lang_of(user_id: int) -> str:
    return USER_LANG.get(
        user_id,
        "en",
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


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await message.answer(
        t("choose_lang", "en"),
        reply_markup=lang_kb(),
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
        t("cancelled", lang)
    )

    await message.answer(
        t("welcome", lang),
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
        t("welcome", lang),
        reply_markup=main_menu_kb(lang),
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
        t("welcome", lang),
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
        t("choose_lang", lang),
        reply_markup=lang_kb(),
    )

    await call.answer()


# ============================================================
# CLEAN MOVIE FORMAT
# ============================================================

def format_movie_card(
    title,
    year,
    kind,
    imdb,
    rt,
    meta,
    rank=None,
    lang="fa",
):
    if kind == "series":
        kind_text = (
            "سریال"
            if lang == "fa"
            else "Series"
        )
    else:
        kind_text = (
            "فیلم"
            if lang == "fa"
            else "Movie"
        )

    if rt is None:
        rt_text = "—"
    else:
        rt_text = f"{rt}%"

    if meta is None:
        meta_text = "—"
    else:
        meta_text = str(meta)

    if rank == 1:
        rank_icon = "🥇"
    elif rank == 2:
        rank_icon = "🥈"
    elif rank == 3:
        rank_icon = "🥉"
    elif rank:
        rank_icon = f"{rank}️⃣"
    else:
        rank_icon = "🎬"

    return (
        f"{rank_icon} <b>{title}</b>\n"
        f"📅 {year} • {kind_text}\n"
        f"⭐ IMDb {imdb}   "
        f"🍅 RT {rt_text}\n"
        f"🎯 Metacritic {meta_text}"
    )


# ============================================================
# IMDb TOP
# ============================================================

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
        key=lambda row: -float(row[4]),
    )

    if lang == "fa":
        header = (
            "🏆 <b>برترین‌های IMDb</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
        )
    else:
        header = (
            "🏆 <b>Top IMDb Movies & Series</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
        )

    cards = []

    # فقط 20 مورد برای خروجی تمیز و خوانا
    for index, row in enumerate(
        sorted_list[:20],
        1,
    ):
        cards.append(
            format_movie_card(
                title=row[1],
                year=row[2],
                kind=row[3],
                imdb=row[4],
                rt=row[5],
                meta=row[6],
                rank=index,
                lang=lang,
            )
        )

    footer = (
        "\n\n━━━━━━━━━━━━━━━━\n"
        "🎬 <b>MovieBot</b>"
    )

    text = (
        header
        + "\n\n".join(cards)
        + footer
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
        t("pick_genre", lang),
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

    for row in IMDB_TOP:
        if genre in row[7]:
            items.append(
                (
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
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
    unique_items = []

    for item in sorted(
        items,
        key=lambda x: -float(x[3]),
    ):
        title = item[0]

        if title not in seen:
            seen.add(title)
            unique_items.append(item)

    unique_items = unique_items[:15]

    cards = []

    for index, row in enumerate(
        unique_items,
        1,
    ):
        cards.append(
            format_movie_card(
                title=row[0],
                year=row[1],
                kind=row[2],
                imdb=row[3],
                rt=row[4],
                meta=row[5],
                rank=index,
                lang=lang,
            )
        )

    if lang == "fa":
        header = (
            f"🎭 <b>{genre}</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
        )
    else:
        header = (
            f"🎭 <b>{genre}</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
        )

    text = (
        header
        + (
            "\n\n".join(cards)
            if cards
            else "😕 موردی پیدا نشد."
        )
        + "\n\n━━━━━━━━━━━━━━━━"
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
                    "language": (
                        "fa-IR"
                        if lang == "fa"
                        else "en-US"
                    ),
                }

                async with session.get(
                    url,
                    params=params,
                    timeout=10,
                ) as response:

                    data = await response.json()

            movies = data.get(
                "results",
                [],
            )

            cards = []

            for movie in movies[:15]:

                title = (
                    movie.get("title")
                    or movie.get(
                        "original_title"
                    )
                    or "Unknown"
                )

                date = movie.get(
                    "release_date"
                ) or "TBA"

                cards.append(
                    f"🎬 <b>{title}</b>\n"
                    f"📅 {date}"
                )

            if lang == "fa":

                header = (
                    "📅 <b>در انتظار اکران</b>\n"
                    "━━━━━━━━━━━━━━━━\n\n"
                )

            else:

                header = (
                    "📅 <b>Upcoming Releases</b>\n"
                    "━━━━━━━━━━━━━━━━\n\n"
                )

            if cards:

                text = (
                    header
                    + "\n\n".join(cards)
                    + "\n\n━━━━━━━━━━━━━━━━\n"
                    "🎬 <b>MovieBot</b>"
                )

            else:

                text = (
                    header
                    + "😕 فیلمی پیدا نشد."
                )

            await call.message.edit_text(
                text[:4090],
                reply_markup=back_kb(lang),
            )

            await call.answer()

            return

        except Exception:

            logger.exception(
                "TMDB upcoming request failed"
            )

    # Fallback داخلی

    if lang == "fa":

        header = (
            "📅 <b>در انتظار اکران</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
        )

    else:

        header = (
            "📅 <b>Upcoming Releases</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
        )

    cards = []

    for title, date, desc in UPCOMING:

        cards.append(
            f"🎬 <b>{title}</b>\n"
            f"📅 {date}\n"
            f"📝 {desc}"
        )

    text = (
        header
        + "\n\n".join(cards)
        + "\n\n━━━━━━━━━━━━━━━━\n"
        "🎬 <b>MovieBot</b>"
    )

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_kb(lang),
    )

    await call.answer()


# ============================================================
# ACTOR SEARCH
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
        t("ask_actor_name", lang),
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
    lang = lang_of(
        message.from_user.id
    )

    name = message.text.strip().lower()

    result = ACTORS.get(name)

    if not result and TMDB_API_KEY:

        result = await tmdb_person_credits(
            message.text.strip()
        )

    if result:

        cards = []

        for index, title in enumerate(
            result[:10],
            1,
        ):
            cards.append(
                f"{index}. 🎬 {title}"
            )

        text = (
            f"🎭 <b>{message.text.strip()}</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(cards)
        )

        await message.answer(
            text,
            reply_markup=back_kb(lang),
        )

    else:

        await message.answer(
            "😕 <b>بازیگر پیدا نشد.</b>",
            reply_markup=back_kb(lang),
        )

    await state.clear()


# ============================================================
# TMDB PERSON
# ============================================================

async def tmdb_person_credits(
    name: str,
):

    if not TMDB_API_KEY:
        return None

    try:

        async with aiohttp.ClientSession() as session:

            search_url = (
                "https://api.themoviedb.org/3/search/person"
            )

            search_params = {
                "api_key": TMDB_API_KEY,
                "query": name,
            }

            async with session.get(
                search_url,
                params=search_params,
                timeout=10,
            ) as response:

                data = await response.json()

            results = data.get(
                "results",
                [],
            )

            if not results:
                return None

            person_id = results[0].get(
                "id"
            )

            if not person_id:
                return None

            credits_url = (
                f"https://api.themoviedb.org/3/person/"
                f"{person_id}/movie_credits"
            )

            credits_params = {
                "api_key": TMDB_API_KEY,
            }

            async with session.get(
                credits_url,
                params=credits_params,
                timeout=10,
            ) as response:

                credits = await response.json()

            movies = (
                credits.get("cast", [])
                + credits.get("crew", [])
            )

            movies.sort(
                key=lambda x: x.get(
                    "popularity",
                    0,
                ),
                reverse=True,
            )

            result = []

            for movie in movies[:10]:

                title = (
                    movie.get("title")
                    or movie.get(
                        "original_title"
                    )
                )

                year = (
                    movie.get(
                        "release_date"
                    )
                    or ""
                )[:4]

                if title:

                    if year:
                        result.append(
                            f"{title} ({year})"
                        )
                    else:
                        result.append(
                            title
                        )

            return result

    except Exception:

        logger.exception(
            "TMDB person search failed"
        )

        return None


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
        t("ask_director_name", lang),
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
    lang = lang_of(
        message.from_user.id
    )

    name = message.text.strip().lower()

    result = DIRECTORS.get(name)

    if not result and TMDB_API_KEY:

        result = await tmdb_person_credits(
            message.text.strip()
        )

    if result:

        cards = []

        for index, title in enumerate(
            result[:10],
            1,
        ):
            cards.append(
                f"{index}. 🎬 {title}"
            )

        text = (
            f"🎬 <b>{message.text.strip()}</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(cards)
        )

        await message.answer(
            text,
            reply_markup=back_kb(lang),
        )

    else:

        await message.answer(
            "😕 <b>کارگردان پیدا نشد.</b>",
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
        t("ask_movie_name", lang),
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
    lang = lang_of(
        message.from_user.id
    )

    query = message.text.strip()

    imdb = None
    rt = None
    meta = None

    for row in IMDB_TOP:

        if row[1].lower() == query.lower():

            imdb = row[4]
            rt = row[5]
            meta = row[6]

            break

    if imdb is None and OMDB_API_KEY:

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

            if data.get("Response") == "True":

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

                        imdb = value.split(
                            "/"
                        )[0]

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

                        meta = value.split(
                            "/"
                        )[0]

        except Exception:

            logger.exception(
                "OMDb comparison failed"
            )

    if (
        imdb is None
        and rt is None
        and meta is None
    ):

        text = (
            f"🔎 <b>{query}</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "😕 اطلاعاتی برای این فیلم پیدا نشد."
        )

    else:

        text = (
            f"🎬 <b>{query}</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"⭐ IMDb: <b>{imdb or '—'}</b>/10\n"
            f"🍅 Rotten Tomatoes: <b>{rt or '—'}</b>%\n"
            f"🎯 Metacritic: <b>{meta or '—'}</b>/100"
        )

    await message.answer(
        text,
        reply_markup=back_kb(lang),
    )

    await state.clear()


# ============================================================
# SMART RECOMMENDATION
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

    await state.clear()

    await call.message.edit_text(
        t("start_quiz", lang)
    )

    await call.message.answer(
        t("q_mood", lang),
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
        t("q_genre", lang),
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
        t("q_mbti", lang),
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
        t("q_liked", lang)
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

    text = message.text.strip()

    liked = (
        []
        if text == "-"
        else [
            item.strip()
            for item in text.split(",")
            if item.strip()
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

    text = message.text.strip()

    disliked = (
        []
        if text == "-"
        else [
            item.strip()
            for item in text.split(",")
            if item.strip()
        ]
    )

    await message.answer(
        "🎬 <b>در حال تحلیل سلیقه شما...</b>\n"
        "⏳ چند لحظه صبر کنید."
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
            "😕 متأسفانه پیشنهاد مناسبی پیدا نشد.",
            reply_markup=back_kb(lang),
        )

        await state.clear()
        return

    cards = []

    for index, item in enumerate(
        results,
        1,
    ):

        rt = item.get("rt")

        meta = item.get("meta")

        rt_text = (
            f"{rt}%"
            if rt is not None
            else "—"
        )

        meta_text = (
            str(meta)
            if meta is not None
            else "—"
        )

        genres = item.get(
            "genres",
            [],
        )

        genre_text = (
            ", ".join(genres)
            if genres
            else "—"
        )

        cards.append(
            f"{index}. 🎬 <b>{item['title']}</b>\n"
            f"📅 {item['year']}\n"
            f"🎭 {genre_text}\n"
            f"⭐ IMDb {item['imdb']}   "
            f"🍅 RT {rt_text}\n"
            f"🎯 Metacritic {meta_text}"
        )

    text_output = (
        "✨ <b>پیشنهادهای مخصوص شما</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(cards)
        + "\n\n━━━━━━━━━━━━━━━━\n"
        "🎬 <b>MovieBot</b>"
    )

    await message.answer(
        text_output[:4090],
        reply_markup=back_kb(lang),
    )

    await state.clear()


# ============================================================
# AUTOMATIC MOVIE SEARCH
# ============================================================

def movie_result_keyboard(
    movie_id: int,
):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📺 سرویس‌های تماشا",
                    callback_data=f"providers:{movie_id}",
                )
            ]
        ]
    )


async def send_movie_result(
    message: Message,
    movie: dict,
):
    title = (
        movie.get("title")
        or movie.get(
            "original_title"
        )
        or "Unknown"
    )

    release_date = (
        movie.get("release_date")
        or ""
    )

    year = (
        release_date[:4]
        if release_date
        else "—"
    )

    rating = movie.get(
        "vote_average",
        0,
    )

    overview = (
        movie.get("overview")
        or "توضیحی برای این فیلم ثبت نشده است."
    )

    # کوتاه کردن توضیحات
    if len(overview) > 500:
        overview = (
            overview[:497]
            + "..."
        )

    text = (
        "🎬 <b>"
        + title
        + "</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"📅 سال: {year}\n"
        f"⭐ امتیاز: {float(rating):.1f}/10\n\n"
        f"📝 {overview}\n\n"
        "━━━━━━━━━━━━━━━━"
    )

    await message.answer(
        text[:4090],
        reply_markup=movie_result_keyboard(
            movie.get("id")
        ),
    )


@router.callback_query(
    F.data.startswith("providers:")
)
async def show_providers(
    call: CallbackQuery,
):
    try:

        movie_id = int(
            call.data.split(
                ":",
                1,
            )[1]
        )

    except (
        ValueError,
        IndexError,
    ):

        await call.answer(
            "شناسه فیلم نامعتبر است.",
            show_alert=True,
        )

        return

    await call.answer(
        "🔎 در حال بررسی سرویس‌ها..."
    )

    providers = await get_watch_providers(
        movie_id
    )

    if not providers:

        await call.message.answer(
            "📺 <b>سرویس تماشا</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "😕 برای این فیلم سرویس قابل نمایش "
            "پیدا نشد."
        )

        return

    text = providers_text(
        providers
    )

    text = (
        "📺 <b>گزینه‌های تماشا</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        + text
        + "\n\n━━━━━━━━━━━━━━━━"
    )

    await call.message.answer(
        text[:4090]
    )


@router.message()
async def automatic_movie_search(
    message: Message,
    state: FSMContext,
):
    """
    جستجوی خودکار فیلم.

    کاربر فقط اسم فیلم را ارسال می‌کند.
    """

    if not message.text:
        return

    text = message.text.strip()

    if len(text) < 2:
        return

    # اگر کاربر در یک State است،
    # handler مخصوص آن State باید پیام را بگیرد.
    current_state = await state.get_state()

    if current_state:
        return

    # دستورات را جستجو نکن
    if text.startswith("/"):
        return

    lang = lang_of(
        message.from_user.id
    )

    if not TMDB_API_KEY:

        await message.answer(
            "⚠️ <b>جستجوی خودکار فعال نیست.</b>\n\n"
            "TMDB_API_KEY در Environment Variables "
            "تنظیم نشده است."
        )

        return

    searching = await message.answer(
        "🔎 <b>در حال جستجو...</b>\n"
        "⏳ یک لحظه صبر کن."
    )

    try:

        results = await search_movies(
            text,
            language=(
                "fa-IR"
                if lang == "fa"
                else "en-US"
            ),
        )

        # اگر فارسی نتیجه نداد، انگلیسی
        if not results:

            results = await search_movies(
                text,
                language="en-US",
            )

        if not results:

            await searching.edit_text(
                "😕 <b>فیلم پیدا نشد.</b>\n\n"
                "نام فیلم را دقیق‌تر بنویس."
            )

            return

        # بهترین نتیجه
        movie = results[0]

        await searching.delete()

        await send_movie_result(
            message,
            movie,
        )

    except Exception:

        logger.exception(
            "Automatic movie search failed"
        )

        try:

            await searching.edit_text(
                "❌ خطایی هنگام جستجوی فیلم رخ داد.\n"
                "لطفاً دوباره امتحان کن."
            )

        except Exception:
            pass


# ============================================================
# MAIN
# ============================================================

async def main():

    if not BOT_TOKEN:

        raise SystemExit(
            "BOT_TOKEN is missing. "
            "Set BOT_TOKEN in Render Environment Variables."
        )

    if ":" not in BOT_TOKEN:

        raise SystemExit(
            "BOT_TOKEN appears to be invalid."
        )

    # ساخت دیتابیس فیلم
    init_movie_db()

    logger.info(
        "Starting MovieBot..."
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

    # polling
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

    keep_alive()

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "MovieBot stopped manually."
    )
