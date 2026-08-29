import asyncio
import logging
import os
from datetime import date, datetime
from threading import Thread
from urllib.parse import quote_plus

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
# ADMIN
# ============================================================

from admin import (
    admin_router,
    init_admin_db,
    track_user,
    track_search,
    track_usage,
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
# FLASK / RENDER
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
# ROUTER
# ============================================================

router = Router()


# ============================================================
# USER LANGUAGE
# ============================================================

USER_LANG: dict[int, str] = {}


def lang_of(uid: int) -> str:
    return USER_LANG.get(
        uid,
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
# UI FORMATTERS
# ============================================================

DIVIDER = "━━━━━━━━━━━━━━"


def clean_text(value):
    if value is None:
        return "—"

    value = str(value).strip()

    if not value:
        return "—"

    return value


def movie_card(
    title,
    year=None,
    imdb=None,
    rt=None,
    meta=None,
    genres=None,
    lang="en",
):
    """
    خروجی استاندارد اطلاعات فیلم
    """

    title = clean_text(title)

    lines = [
        f"🎬 <b>{title}</b>",
    ]

    if year:
        lines.append(
            f"📅 {clean_text(year)}"
        )

    scores = []

    if imdb is not None:
        scores.append(
            f"⭐ IMDb {imdb}"
        )

    if rt is not None:
        scores.append(
            f"🍅 RT {rt}%"
        )

    if meta is not None:
        scores.append(
            f"🎯 Metacritic {meta}"
        )

    if scores:
        lines.append(
            "   ".join(scores)
        )

    if genres:
        if isinstance(genres, (list, tuple)):
            genre_text = ", ".join(
                str(x)
                for x in genres
                if x
            )
        else:
            genre_text = str(genres)

        if genre_text:
            lines.append(
                f"🏷 {genre_text}"
            )

    return "\n".join(lines)


def section_header(
    title,
    emoji="🎬",
):
    return (
        f"{emoji} <b>{title}</b>\n"
        f"{DIVIDER}\n"
    )


def footer(lang="en"):
    if lang == "fa":
        return (
            f"\n{DIVIDER}\n"
            "🎬 <b>MovieBot</b>"
        )

    return (
        f"\n{DIVIDER}\n"
        "🎬 <b>MovieBot</b>"
    )


# ============================================================
# DATE FORMAT
# ============================================================

MONTHS_EN = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


MONTHS_FA = {
    1: "ژانویه",
    2: "فوریه",
    3: "مارس",
    4: "آوریل",
    5: "مه",
    6: "ژوئن",
    7: "ژوئیه",
    8: "اوت",
    9: "سپتامبر",
    10: "اکتبر",
    11: "نوامبر",
    12: "دسامبر",
}


def format_date(
    value,
    lang="en",
):
    if not value:
        return "TBA"

    try:

        dt = datetime.strptime(
            str(value),
            "%Y-%m-%d",
        )

        if lang == "fa":

            return (
                f"{dt.day} "
                f"{MONTHS_FA[dt.month]} "
                f"{dt.year}"
            )

        return (
            f"{MONTHS_EN[dt.month]} "
            f"{dt.day}, "
            f"{dt.year}"
        )

    except Exception:

        return str(value)


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
):

    user = message.from_user

    if user is None:
        return

    await track_user(user)

    await track_usage(
        user.id,
        "start",
    )

    await state.clear()

    await message.answer(
        t(
            "choose_lang",
            "en",
        ),
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

    user = message.from_user

    if user is None:
        return

    await track_user(user)

    await track_usage(
        user.id,
        "cancel",
    )

    await state.clear()

    lang = lang_of(
        user.id
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "language_change",
    )

    lang = call.data.split(
        ":",
        1,
    )[1]

    USER_LANG[user.id] = lang

    await call.message.edit_text(
        t(
            "welcome",
            lang,
        ),
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "home",
    )

    await state.clear()

    lang = lang_of(
        user.id
    )

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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "language_menu",
    )

    lang = lang_of(
        user.id
    )

    await call.message.edit_text(
        t(
            "choose_lang",
            lang,
        ),
        reply_markup=lang_kb(),
    )

    await call.answer()


# ============================================================
# IMDb TOP
# ============================================================

@router.callback_query(
    F.data == "menu:top250"
)
async def top250(
    call: CallbackQuery,
):

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "top250",
    )

    lang = lang_of(
        user.id
    )

    sorted_list = sorted(
        IMDB_TOP,
        key=lambda r: -r[4],
    )

    cards = []

    for i, r in enumerate(
        sorted_list[:25],
        1,
    ):

        card = movie_card(
            title=r[1],
            year=r[2],
            imdb=r[4],
            rt=r[5],
            meta=r[6],
            lang=lang,
        )

        cards.append(
            f"<b>{i}.</b>\n{card}"
        )

    if lang == "fa":

        header = section_header(
            "برترین فیلم‌ها",
            "🏆",
        )

    else:

        header = section_header(
            "Top IMDb Movies",
            "🏆",
        )

    text = (
        header
        + "\n\n".join(cards)
        + footer(lang)
    )

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_kb(lang),
    )

    await call.answer()


# ============================================================
# GENRE
# ============================================================

@router.callback_query(
    F.data == "menu:genre"
)
async def menu_genre(
    call: CallbackQuery,
):

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "genre_menu",
    )

    lang = lang_of(
        user.id
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

    user = call.from_user

    await track_user(user)

    await track_search(
        user.id,
        "genre",
    )

    lang = lang_of(
        user.id
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

    uniq = uniq[:15]

    cards = []

    for i, row in enumerate(
        uniq,
        1,
    ):

        cards.append(
            f"<b>{i}.</b>\n"
            + movie_card(
                title=row[0],
                year=row[1],
                imdb=row[3],
                rt=row[4],
                meta=row[5],
                lang=lang,
            )
        )

    if lang == "fa":

        header = section_header(
            f"فیلم‌های {genre}",
            "🎬",
        )

    else:

        header = section_header(
            f"{genre} Movies",
            "🎬",
        )

    text = (
        header
        + "\n\n".join(cards)
        + footer(lang)
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "upcoming",
    )

    lang = lang_of(
        user.id
    )

    # --------------------------------------------------------
    # TMDB LIVE
    # --------------------------------------------------------

    if TMDB_API_KEY:

        try:

            async with aiohttp.ClientSession() as session:

                url = (
                    "https://api.themovied.org/3/movie/upcoming"
                    f"?api_key={TMDB_API_KEY}"
                    f"&language={'fa' if lang == 'fa' else 'en'}-US"
                )

                # اصلاح دامنه
                url = url.replace(
                    "api.themov.org",
                    "api.themoviedb.org",
                )

                async with session.get(
                    url,
                    timeout=10,
                ) as response:

                    data = await response.json()

            today = date.today()

            movies = []

            for movie in data.get(
                "results",
                [],
            ):

                release = movie.get(
                    "release_date"
                )

                if not release:
                    continue

                try:

                    release_date = datetime.strptime(
                        release,
                        "%Y-%m-%d",
                    ).date()

                except Exception:

                    continue

                # فقط فیلم‌های امروز به بعد
                if release_date >= today:

                    movies.append(
                        movie
                    )

            movies = movies[:15]

            if lang == "fa":

                header = section_header(
                    "فیلم‌های در انتظار اکران",
                    "📅",
                )

            else:

                header = section_header(
                    "Upcoming Movies",
                    "📅",
                )

            cards = []

            for i, movie in enumerate(
                movies,
                1,
            ):

                title = (
                    movie.get("title")
                    or movie.get("original_title")
                    or "Unknown"
                )

                release = movie.get(
                    "release_date"
                )

                cards.append(
                    f"<b>{i}.</b> "
                    f"<b>{clean_text(title)}</b>\n"
                    f"📅 {format_date(release, lang)}"
                )

            if cards:

                text = (
                    header
                    + "\n\n".join(cards)
                    + footer(lang)
                )

            else:

                if lang == "fa":

                    text = (
                        header
                        + "در حال حاضر فیلمی برای نمایش پیدا نشد."
                        + footer(lang)
                    )

                else:

                    text = (
                        header
                        + "No upcoming movies were found."
                        + footer(lang)
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

    # --------------------------------------------------------
    # STATIC FALLBACK
    # --------------------------------------------------------

    if lang == "fa":

        header = section_header(
            "فیلم‌های در انتظار اکران",
            "📅",
        )

    else:

        header = section_header(
            "Upcoming Movies",
            "📅",
        )

    today = date.today()

    cards = []

    for title, release, desc in UPCOMING:

        try:

            release_date = datetime.strptime(
                str(release),
                "%Y-%m-%d",
            ).date()

        except Exception:

            release_date = None

        if release_date and release_date < today:
            continue

        cards.append(
            f"🎬 <b>{clean_text(title)}</b>\n"
            f"📅 {format_date(release, lang)}"
        )

    cards = cards[:15]

    if cards:

        text = (
            header
            + "\n\n".join(cards)
            + footer(lang)
        )

    else:

        text = (
            header
            + (
                "در حال حاضر موردی وجود ندارد."
                if lang == "fa"
                else "No upcoming movies found."
            )
            + footer(lang)
        )

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_kb(lang),
    )

    await call.answer()


# ============================================================
# TMDB PERSON
# ============================================================

async def _tmdb_person_credits(
    name: str,
    lang: str,
):

    if not TMDB_API_KEY:
        return None

    encoded_name = quote_plus(
        name
    )

    async with aiohttp.ClientSession() as session:

        search_url = (
            "https://api.themoviedb.org/3/search/person"
            f"?api_key={TMDB_API_KEY}"
            f"&query={encoded_name}"
        )

        async with session.get(
            search_url,
            timeout=10,
        ) as response:

            data = await response.json()

        results = data.get(
            "results",
            [],
        )

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
            credits.get(
                "cast",
                [],
            )
            + credits.get(
                "crew",
                [],
            ),
            key=lambda movie: movie.get(
                "popularity",
                0,
            ),
            reverse=True,
        )

        result = []

        seen = set()

        for movie in cast:

            title = movie.get(
                "title"
            )

            if not title:
                continue

            if title in seen:
                continue

            seen.add(
                title
            )

            release = (
                movie.get(
                    "release_date"
                )
                or ""
            )

            year = (
                release[:4]
                if release
                else "TBA"
            )

            result.append(
                (
                    title,
                    year,
                )
            )

            if len(result) >= 10:
                break

        return result


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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "actor_menu",
    )

    lang = lang_of(
        user.id
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

    user = message.from_user

    if user is None:
        return

    await track_user(user)

    await track_search(
        user.id,
        "actor",
    )

    lang = lang_of(
        user.id
    )

    query = message.text.strip()

    result = ACTORS.get(
        query.lower()
    )

    if not result and TMDB_API_KEY:

        result = await _tmdb_person_credits(
            query,
            lang,
        )

    if result:

        header = section_header(
            f"آثار {query}"
            if lang == "fa"
            else f"Works by {query}",
            "🎭",
        )

        lines = []

        for i, item in enumerate(
            result[:10],
            1,
        ):

            if isinstance(
                item,
                tuple,
            ):

                title = item[0]
                year = item[1]

            else:

                title = str(item)
                year = None

            lines.append(
                f"<b>{i}.</b> "
                f"{clean_text(title)}"
                + (
                    f"\n📅 {year}"
                    if year
                    else ""
                )
            )

        text = (
            header
            + "\n\n".join(lines)
            + footer(lang)
        )

        await message.answer(
            text[:4090],
            reply_markup=back_kb(lang),
        )

    else:

        await message.answer(
            t(
                "not_found_local",
                lang,
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "director_menu",
    )

    lang = lang_of(
        user.id
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

    user = message.from_user

    if user is None:
        return

    await track_user(user)

    await track_search(
        user.id,
        "director",
    )

    lang = lang_of(
        user.id
    )

    query = message.text.strip()

    result = DIRECTORS.get(
        query.lower()
    )

    if not result and TMDB_API_KEY:

        result = await _tmdb_person_credits(
            query,
            lang,
        )

    if result:

        header = section_header(
            f"آثار {query}"
            if lang == "fa"
            else f"Works by {query}",
            "🎬",
        )

        lines = []

        for i, item in enumerate(
            result[:10],
            1,
        ):

            if isinstance(
                item,
                tuple,
            ):

                title = item[0]
                year = item[1]

            else:

                title = str(item)
                year = None

            lines.append(
                f"<b>{i}.</b> "
                f"{clean_text(title)}"
                + (
                    f"\n📅 {year}"
                    if year
                    else ""
                )
            )

        text = (
            header
            + "\n\n".join(lines)
            + footer(lang)
        )

        await message.answer(
            text[:4090],
            reply_markup=back_kb(lang),
        )

    else:

        await message.answer(
            t(
                "not_found_local",
                lang,
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "compare_menu",
    )

    lang = lang_of(
        user.id
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

    user = message.from_user

    if user is None:
        return

    await track_user(user)

    await track_search(
        user.id,
        "movie_compare",
    )

    lang = lang_of(
        user.id
    )

    query = message.text.strip()

    imdb = None
    rt = None
    meta = None

    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    for r in IMDB_TOP:

        if r[1].lower() == query.lower():

            imdb = r[4]
            rt = r[5]
            meta = r[6]

            break

    # --------------------------------------------------------
    # OMDB
    # --------------------------------------------------------

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
                    f"?apikey={OMDB_API_KEY}"
                    f"&t={quote_plus(query)}"
                )

                async with session.get(
                    url,
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
                        "Value"
                    )

                    if not value:
                        continue

                    if source_name == "Internet Movie Database":

                        imdb = value.split(
                            "/"
                        )[0]

                    elif source_name == "Rotten Tomatoes":

                        rt = value.replace(
                            "%",
                            "",
                        )

                    elif source_name == "Metacritic":

                        meta = value.split(
                            "/"
                        )[0]

        except Exception:

            logger.exception(
                "OMDb request failed"
            )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    if lang == "fa":

        header = section_header(
            f"مقایسه «{query}»",
            "⚖️",
        )

    else:

        header = section_header(
            f"Rating for “{query}”",
            "⚖️",
        )

    if (
        imdb is None
        and rt is None
        and meta is None
    ):

        body = t(
            "not_found_local",
            lang,
        )

    else:

        body = (
            f"⭐ <b>IMDb</b>       {imdb or '—'}/10\n"
            f"🍅 <b>Rotten Tomatoes</b>   {rt or '—'}%\n"
            f"🎯 <b>Metacritic</b>   {meta or '—'}/100"
        )

    await message.answer(
        (
            header
            + body
            + footer(lang)
        )[:4090],
        reply_markup=back_kb(lang),
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "recommendation_quiz",
    )

    lang = lang_of(
        user.id
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "quiz_mood",
    )

    lang = lang_of(
        user.id
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "quiz_genre",
    )

    lang = lang_of(
        user.id
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

    user = call.from_user

    await track_user(user)

    await track_usage(
        user.id,
        "quiz_mbti",
    )

    lang = lang_of(
        user.id
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

    user = message.from_user

    if user is None:
        return

    await track_user(user)

    await track_usage(
        user.id,
        "quiz_liked",
    )

    lang = lang_of(
        user.id
    )

    text = message.text.strip()

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

    user = message.from_user

    if user is None:
        return

    await track_user(user)

    await track_usage(
        user.id,
        "quiz_disliked",
    )

    lang = lang_of(
        user.id
    )

    text = message.text.strip()

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
            (
                "نتیجه‌ای پیدا نشد."
                if lang == "fa"
                else "No recommendations found."
            ),
            reply_markup=back_kb(lang),
        )

        await state.clear()

        return

    header = section_header(
        "پیشنهادهای مخصوص شما"
        if lang == "fa"
        else "Your Recommendations",
        "✨",
    )

    cards = []

    for i, item in enumerate(
        results,
        1,
    ):

        cards.append(
            f"<b>{i}.</b>\n"
            + movie_card(
                title=item["title"],
                year=item["year"],
                imdb=item["imdb"],
                rt=item["rt"],
                meta=item["meta"],
                genres=item["genres"],
                lang=lang,
            )
        )

    text = (
        header
        + "\n\n".join(cards)
        + footer(lang)
    )

    await message.answer(
        text[:4090],
        reply_markup=back_kb(lang),
    )

    await state.clear()


# ============================================================
# MAIN
# ============================================================

async def main():

    if (
        not BOT_TOKEN
        or ":" not in BOT_TOKEN
    ):

        raise SystemExit(
            "BOT_TOKEN is missing/invalid. "
            "Set BOT_TOKEN in Render Environment Variables."
        )

    # Initialize admin DB
    init_admin_db()

    logger.info(
        "Admin database initialized."
    )

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher(
        storage=MemoryStorage()
    )

    # MovieBot
    dp.include_router(
        router
    )

    # Admin
    dp.include_router(
        admin_router
    )

    # Polling
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
            "Bot stopped manually."
    )
