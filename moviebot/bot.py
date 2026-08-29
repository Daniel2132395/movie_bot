# ============================================================
# MovieBot
# aiogram 3.x
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

# ============================================================
# IMPORTS
# ============================================================

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
    region_kb,
)

from locales import t
from recommender import recommend
from movie_db import init_movie_db, save_movie, search_local_movies

from providers import (
    search_movies,
    get_provider_results,
    providers_text,
    movie_text,
)

from admin import admin_router


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("MovieBot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "").strip()
DEFAULT_REGION = os.getenv("WATCH_REGION", "IR").strip().upper()


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
    port = int(os.getenv("PORT", "8080"))
    logger.info("Health server running on port %s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def keep_alive():
    thread = Thread(target=run_web_server, daemon=True)
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
    return USER_LANG.get(user_id, "fa")

def region_of(user_id: int) -> str:
    return USER_REGION.get(user_id, DEFAULT_REGION)


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
    return escape(str(text))

def language_code(user_id: int) -> str:
    return "fa-IR" if lang_of(user_id) == "fa" else "en-US"


# ============================================================
# GET USER ID
# ============================================================

@router.message(Command("id"))
async def get_my_id(message: Message):
    await message.answer(
        f"🆔 آی‌دی شما:\n<code>{message.from_user.id}</code>\n\n"
        f"👤 نام: {message.from_user.first_name}\n"
        f"🔗 یوزرنیم: @{message.from_user.username or 'ندارد'}"
    )


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    USER_LANG.setdefault(user_id, "fa")
    USER_REGION.setdefault(user_id, DEFAULT_REGION)
    lang = lang_of(user_id)

    await message.answer(
        t("welcome", lang),
        reply_markup=main_menu_kb(lang),
    )


# ============================================================
# CANCEL
# ============================================================

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    lang = lang_of(message.from_user.id)
    await message.answer(t("cancelled", lang))
    await message.answer(t("welcome", lang), reply_markup=main_menu_kb(lang))


# ============================================================
# LANGUAGE
# ============================================================

@router.callback_query(F.data.startswith("lang:"))
async def set_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":", 1)[1]
    if lang not in ("fa", "en"):
        await call.answer("Language error", show_alert=True)
        return

    USER_LANG[call.from_user.id] = lang
    await state.clear()
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


@router.callback_query(F.data == "menu:home")
async def menu_home(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = lang_of(call.from_user.id)
    await call.message.edit_text(
        t("welcome", lang),
        reply_markup=main_menu_kb(lang),
    )
    await call.answer()


# ============================================================
# REGION
# ============================================================

@router.callback_query(F.data == "menu:region")
async def choose_region(call: CallbackQuery):
    region = region_of(call.from_user.id)
    await call.message.edit_text(
        f"🌍 <b>منطقه تماشا</b>\n━━━━━━━━━━━━━━━━\n\nمنطقه موردنظر را انتخاب کن.\n\n📍 منطقه فعلی: <b>{clean(region)}</b>",
        reply_markup=region_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("region:"))
async def set_region(call: CallbackQuery):
    region = call.data.split(":", 1)[1].upper()
    allowed = {"IR", "GB", "US", "CA"}
    if region not in allowed:
        await call.answer("منطقه نامعتبر است.", show_alert=True)
        return

    USER_REGION[call.from_user.id] = region
    await call.message.edit_text(
        f"✅ <b>منطقه ذخیره شد</b>\n━━━━━━━━━━━━━━━━\n\n🌍 منطقه: <b>{region}</b>",
        reply_markup=main_menu_kb(lang_of(call.from_user.id)),
    )
    await call.answer("ذخیره شد ✅")


# ============================================================
# SEARCH & WATCH
# ============================================================

@router.callback_query(F.data == "menu:search_watch")
async def search_watch_center(call: CallbackQuery):
    user_id = call.from_user.id
    await call.message.edit_text(
        "🎬 <b>جستجو و تماشای فیلم</b>\n━━━━━━━━━━━━━━━━\n\nنام فیلم یا سریال را وارد کن.\n\nمثال:\n🎬 Breaking Bad\n🎬 Interstellar\n📺 Stranger Things\n\n🔎 جستجو مستقیماً روی سرویس‌های تعریف‌شده انجام می‌شود.",
        reply_markup=search_watch_kb(lang_of(user_id)),
    )
    await call.answer()


# ============================================================
# START SEARCH
# ============================================================

@router.callback_query(F.data == "search:start")
async def search_start(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = lang_of(call.from_user.id)
    await call.message.edit_text(
        "🔎 <b>جستجوی فیلم و سریال</b>\n━━━━━━━━━━━━━━━━\n\nنام فیلم یا سریال را ارسال کن.\n\nمثلاً:\n🎬 Breaking Bad\n🎬 Interstellar\n📺 Dark",
        reply_markup=search_watch_kb(lang),
    )
    await state.set_state(MovieSearch.query)
    await call.answer()


# ============================================================
# PERFORM SEARCH
# ============================================================

async def perform_movie_search(query: str, user_id: int):
    """جستجوی فیلم با اولویت دیتابیس محلی و سپس منابع دیگر"""
    query = query.strip()
    if not query:
        return []

    results = []
    
    # 1. جستجوی توی دیتابیس محلی
    local_results = search_local_movies(query)
    if local_results:
        for i, item in enumerate(local_results):
            results.append({
                "id": item.get("tmdb_id", i + 1),
                "title": item.get("title", query),
                "name": item.get("title", query),
                "original_title": item.get("original_title", query),
                "_media_type": "movie",
                "provider_id": "local",
                "provider_name": "📚 دیتابیس داخلی",
                "provider_url": "",
                "url": "",
                "release_date": str(item.get("year", "")),
                "vote_average": item.get("vote_average", 0),
                "overview": item.get("overview", "اطلاعات بیشتری در دیتابیس موجود نیست."),
            })
    
    # 2. جستجوی توی IMDb از طریق OMDb (اگه کلید داشته باشیم)
    if OMDB_API_KEY and len(results) < 5:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.omdbapi.com/",
                    params={"apikey": OMDB_API_KEY, "s": query},
                    timeout=10,
                ) as response:
                    data = await response.json()
                    
                    if data.get("Response") == "True":
                        for item in data.get("Search", [])[:10]:
                            # دریافت جزئیات بیشتر برای هر فیلم
                            try:
                                async with session.get(
                                    "https://www.omdbapi.com/",
                                    params={"apikey": OMDB_API_KEY, "i": item.get("imdbID")},
                                    timeout=10,
                                ) as detail_response:
                                    detail_data = await detail_response.json()
                                    year = detail_data.get("Year", "")
                                    plot = detail_data.get("Plot", "اطلاعات بیشتری موجود نیست.")
                            except:
                                year = item.get("Year", "")
                                plot = "اطلاعات بیشتری موجود نیست."
                            
                            results.append({
                                "id": item.get("imdbID", len(results) + 1),
                                "title": item.get("Title", query),
                                "name": item.get("Title", query),
                                "original_title": item.get("Title", query),
                                "_media_type": "movie",
                                "provider_id": "imdb",
                                "provider_name": "⭐ IMDb (OMDb)",
                                "provider_url": f"https://www.imdb.com/title/{item.get('imdbID', '')}/",
                                "url": f"https://www.imdb.com/title/{item.get('imdbID', '')}/",
                                "release_date": year,
                                "vote_average": None,
                                "overview": plot[:300] + "..." if len(plot) > 300 else plot,
                            })
        except Exception as e:
            logger.error(f"OMDb error: {e}")
    
    # 3. جستجوی توی سرویس‌های ایرانی (اگه نتایج قبلی نبود)
    if not results:
        try:
            iranian_results = await search_movies(
                query=query,
                language=language_code(user_id),
                limit=10,
            )
            results.extend(iranian_results)
        except Exception as e:
            logger.error(f"Iranian providers error: {e}")
    
    return results


@router.message(MovieSearch.query)
async def movie_search(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        await message.answer("❌ لطفاً نام فیلم یا سریال را وارد کن.")
        return

    status_message = await message.answer(
        f"🔎 <b>در حال جستجو...</b>\n\n🎬 <code>{clean(query)}</code>\n\n🌐 در حال جستجو در منابع مختلف..."
    )

    try:
        results = await perform_movie_search(query, message.from_user.id)
    except Exception as e:
        logger.exception("Search failed")
        await status_message.edit_text(
            "⚠️ <b>خطا در جستجو</b>\n\nسرویس جستجو موقتاً در دسترس نیست."
        )
        await state.clear()
        return

    if not results:
        await status_message.edit_text(
            f"😕 <b>نتیجه‌ای پیدا نشد</b>\n━━━━━━━━━━━━━━━━\n\n🔎 {clean(query)}\n\n💡 نکته: برای فیلم‌های جدید از دکمه «جستجوی دوباره» استفاده کن.",
            reply_markup=search_watch_kb(lang_of(message.from_user.id)),
        )
        await state.clear()
        return

    await status_message.edit_text(
        f"🎬 <b>نتیجه جستجو</b>\n━━━━━━━━━━━━━━━━\n\n🔎 عنوان: <b>{clean(query)}</b>\n\n📊 <b>{len(results)} نتیجه پیدا شد</b>\n\nیکی از گزینه‌ها را انتخاب کن:",
        reply_markup=search_results_kb(results),
    )
    await state.clear()


# ============================================================
# PROVIDER RESULT SELECT
# ============================================================

@router.callback_query(F.data.startswith("provider:"))
async def provider_select(call: CallbackQuery):
    provider_id = call.data.split(":", 1)[1]

    # Get query from message text
    query = ""
    if call.message and call.message.text:
        text = call.message.text
        marker = "🔎 عنوان:"
        if marker in text:
            query = text.split(marker, 1)[1].split("\n", 1)[0].strip()
            query = query.replace("<b>", "").replace("</b>", "")

    if not query:
        await call.message.answer("⚠️ عنوان جستجو قابل تشخیص نیست.")
        return

    # Try to get results from providers
    results = await get_provider_results(query)
    selected = None
    
    # First check if it's a local or IMDb result
    if provider_id == "local":
        # Local database result - show details
        local_results = search_local_movies(query)
        if local_results:
            item = local_results[0]
            await call.message.edit_text(
                f"🎬 <b>{clean(item.get('title', query))}</b>\n━━━━━━━━━━━━━━━━\n\n"
                f"📅 سال: {item.get('year', 'نامشخص')}\n"
                f"📚 منبع: دیتابیس داخلی\n\n"
                f"📝 {clean(item.get('overview', 'اطلاعات بیشتری موجود نیست.'))}",
                reply_markup=movie_result_kb("local", "", query),
            )
            await call.answer()
            return
    
    elif provider_id == "imdb":
        # IMDb result - show details with link
        await call.message.edit_text(
            f"🎬 <b>{clean(query)}</b>\n━━━━━━━━━━━━━━━━\n\n"
            f"⭐ منبع: IMDb\n\n"
            f"🔗 برای مشاهده جزئیات بیشتر روی دکمه زیر کلیک کن:",
            reply_markup=movie_result_kb(
                "imdb", 
                f"https://www.imdb.com/find?q={query.replace(' ', '+')}", 
                query
            ),
        )
        await call.answer()
        return
    
    # Iranian providers
    for item in results:
        if item.get("provider_id") == provider_id:
            selected = item
            break

    if not selected:
        await call.message.answer("⚠️ سرویس موردنظر پیدا نشد.")
        return

    name = clean(selected.get("provider_name", "سرویس"))
    url = selected.get("url")

    if not url:
        await call.message.answer("⚠️ لینک سرویس موجود نیست.")
        return

    text = f"🎬 <b>نتیجه جستجو</b>\n━━━━━━━━━━━━━━━━\n\n🔎 عنوان: <b>{clean(query)}</b>\n\n🇮🇷 سرویس: <b>{name}</b>\n\nبرای مشاهده نتیجه، روی دکمه زیر بزن:"

    await call.message.edit_text(
        text,
        reply_markup=movie_result_kb(provider_id, url, query),
    )
    await call.answer()


# ============================================================
# TOP IMDb
# ============================================================

def _fmt_entry(idx, title, year, kind, imdb, rt, meta, lang):
    kind_label = "سریال" if kind == "series" and lang == "fa" else "فیلم" if lang == "fa" else "Series" if kind == "series" else "Movie"
    rt_s = f"{rt}%" if rt is not None else "—"
    meta_s = str(meta) if meta is not None else "—"
    return f"{idx}. 🎬 <b>{clean(title)}</b> ({year})\n   {kind_label} • ⭐ IMDb {imdb} • 🍅 RT {rt_s} • Ⓜ️ {meta_s}"


@router.callback_query(F.data == "menu:top250")
async def top250(call: CallbackQuery):
    lang = lang_of(call.from_user.id)
    sorted_list = sorted(IMDB_TOP, key=lambda r: -r[4])
    lines = []
    for i, r in enumerate(sorted_list[:40], 1):
        lines.append(_fmt_entry(i, r[1], r[2], r[3], r[4], r[5], r[6], lang))

    text = "🏆 <b>برترین‌های IMDb</b>\n━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(lines)
    await call.message.edit_text(text[:4090], reply_markup=back_kb(lang))
    await call.answer()


# ============================================================
# GENRES
# ============================================================

@router.callback_query(F.data == "menu:genre")
async def menu_genre(call: CallbackQuery):
    lang = lang_of(call.from_user.id)
    await call.message.edit_text(t("pick_genre", lang), reply_markup=genre_kb(lang))
    await call.answer()


@router.callback_query(F.data.startswith("genre:"))
async def show_genre(call: CallbackQuery):
    lang = lang_of(call.from_user.id)
    genre = call.data.split(":", 1)[1]

    items = []
    for r in IMDB_TOP:
        if genre in r[7]:
            items.append((r[1], r[2], r[3], r[4], r[5], r[6]))

    for item in GENRE_EXTRA.get(genre, []):
        items.append((item[0], item[1], item[2], item[3], item[4], item[5]))

    seen = set()
    uniq = []
    for item in sorted(items, key=lambda x: -x[3]):
        if item[0] not in seen:
            seen.add(item[0])
            uniq.append(item)

    lines = []
    for i, row in enumerate(uniq[:25], 1):
        lines.append(_fmt_entry(i, *row, lang))

    text = f"🎭 <b>{clean(genre)}</b>\n━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(lines)
    await call.message.edit_text(text[:4090], reply_markup=genre_kb(lang))
    await call.answer()


# ============================================================
# UPCOMING
# ============================================================

@router.callback_query(F.data == "menu:upcoming")
async def upcoming(call: CallbackQuery):
    lang = lang_of(call.from_user.id)
    lines = []
    for title, date, desc in UPCOMING:
        lines.append(f"🎬 <b>{clean(title)}</b>\n   📅 {clean(date)}\n   {clean(desc)}")

    text = "📅 <b>در انتظار اکران</b>\n━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(lines)
    await call.message.edit_text(text[:4090], reply_markup=back_kb(lang))
    await call.answer()


# ============================================================
# ACTOR
# ============================================================

@router.callback_query(F.data == "menu:actor")
async def ask_actor(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await call.message.edit_text(t("ask_actor_name", lang), reply_markup=back_kb(lang))
    await state.set_state(TextSearch.actor)
    await call.answer()


@router.message(TextSearch.actor)
async def do_actor_search(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    lang = lang_of(message.from_user.id)
    result = ACTORS.get(query.lower())

    if result:
        lines = []
        for i, item in enumerate(result, 1):
            lines.append(f"{i}. 🎬 {clean(item)}")
        await message.answer(
            f"🎭 <b>{clean(query)}</b>\n━━━━━━━━━━━━━━━━\n\n" + "\n".join(lines),
            reply_markup=back_kb(lang),
        )
    else:
        await message.answer("😕 بازیگر موردنظر پیدا نشد.", reply_markup=back_kb(lang))

    await state.clear()


# ============================================================
# DIRECTOR
# ============================================================

@router.callback_query(F.data == "menu:director")
async def ask_director(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await call.message.edit_text(t("ask_director_name", lang), reply_markup=back_kb(lang))
    await state.set_state(TextSearch.director)
    await call.answer()


@router.message(TextSearch.director)
async def do_director_search(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    lang = lang_of(message.from_user.id)
    result = DIRECTORS.get(query.lower())

    if result:
        lines = []
        for i, item in enumerate(result, 1):
            lines.append(f"{i}. 🎬 {clean(item)}")
        await message.answer(
            f"🎬 <b>{clean(query)}</b>\n━━━━━━━━━━━━━━━━\n\n" + "\n".join(lines),
            reply_markup=back_kb(lang),
        )
    else:
        await message.answer("😕 کارگردان موردنظر پیدا نشد.", reply_markup=back_kb(lang))

    await state.clear()


# ============================================================
# COMPARE
# ============================================================

@router.callback_query(F.data == "menu:compare")
async def ask_compare(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await call.message.edit_text(t("ask_movie_name", lang), reply_markup=back_kb(lang))
    await state.set_state(TextSearch.movie)
    await call.answer()


@router.message(TextSearch.movie)
async def do_compare(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    lang = lang_of(message.from_user.id)

    imdb = None
    rt = None
    meta = None

    for r in IMDB_TOP:
        if r[1].lower() == query.lower():
            imdb = r[4]
            rt = r[5]
            meta = r[6]
            break

    if imdb is None and rt is None and meta is None and OMDB_API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.omdbapi.com/",
                    params={"apikey": OMDB_API_KEY, "t": query},
                    timeout=10,
                ) as response:
                    data = await response.json()

            if data.get("Response") == "True":
                for source in data.get("Ratings", []):
                    name = source.get("Source")
                    value = source.get("Value", "")
                    if name == "Internet Movie Database":
                        imdb = value.split("/")[0]
                    elif name == "Rotten Tomatoes":
                        rt = value.replace("%", "")
                    elif name == "Metacritic":
                        meta = value.split("/")[0]
        except Exception:
            logger.exception("OMDb request failed")

    if imdb is None and rt is None and meta is None:
        text = f"😕 <b>عنوان پیدا نشد</b>\n━━━━━━━━━━━━━━━━\n\n🔎 {clean(query)}"
    else:
        text = f"🎬 <b>{clean(query)}</b>\n━━━━━━━━━━━━━━━━\n\n⭐ IMDb: <b>{imdb or '—'}</b>/10\n🍅 Rotten Tomatoes: <b>{rt or '—'}</b>%\nⓂ️ Metacritic: <b>{meta or '—'}</b>/100"

    await message.answer(text, reply_markup=back_kb(lang))
    await state.clear()


# ============================================================
# RECOMMENDATION
# ============================================================

@router.callback_query(F.data == "menu:recommend")
async def start_quiz(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await call.message.edit_text(t("q_mood", lang), reply_markup=mood_kb(lang))
    await state.set_state(Quiz.mood)
    await call.answer()


@router.callback_query(Quiz.mood, F.data.startswith("mood:"))
async def quiz_mood(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await state.update_data(mood=call.data.split(":", 1)[1])
    await call.message.edit_text(t("q_genre", lang), reply_markup=quiz_genre_kb(lang))
    await state.set_state(Quiz.genre)
    await call.answer()


@router.callback_query(Quiz.genre, F.data.startswith("qgenre:"))
async def quiz_genre(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await state.update_data(genre=call.data.split(":", 1)[1])
    await call.message.edit_text(t("q_mbti", lang), reply_markup=mbti_kb(lang))
    await state.set_state(Quiz.mbti)
    await call.answer()


@router.callback_query(Quiz.mbti, F.data.startswith("mbti:"))
async def quiz_mbti(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await state.update_data(mbti=call.data.split(":", 1)[1])
    await call.message.edit_text(t("q_liked", lang))
    await state.set_state(Quiz.liked)
    await call.answer()


@router.message(Quiz.liked)
async def quiz_liked(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    liked = [] if text == "-" else [x.strip() for x in text.split(",") if x.strip()]
    await state.update_data(liked=liked)
    await message.answer(t("q_disliked", lang_of(message.from_user.id)))
    await state.set_state(Quiz.disliked)


@router.message(Quiz.disliked)
async def quiz_disliked(message: Message, state: FSMContext):
    lang = lang_of(message.from_user.id)
    text = (message.text or "").strip()
    disliked = [] if text == "-" else [x.strip() for x in text.split(",") if x.strip()]

    await message.answer(t("analyzing", lang))

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
    for i, item in enumerate(results, 1):
        rt_s = f"{item['rt']}%" if item["rt"] is not None else "—"
        meta_s = str(item["meta"]) if item["meta"] is not None else "—"
        lines.append(
            f"{i}. 🎬 <b>{clean(item['title'])}</b> ({item['year']})\n"
            f"   🎭 {', '.join(item['genres'])}\n"
            f"   ⭐ IMDb {item['imdb']} • 🍅 RT {rt_s} • Ⓜ️ {meta_s}"
        )

    await message.answer(
        t("recommend_header", lang) + "\n\n" + "\n\n".join(lines),
        reply_markup=back_kb(lang),
    )
    await state.clear()


# ============================================================
# FALLBACK
# ============================================================

@router.message()
async def fallback_text_search(message: Message):
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    await message.answer(
        "🔎 <b>برای جستجو</b>\n\nاز منوی «جستجو و تماشای فیلم» استفاده کن.",
        reply_markup=search_watch_kb(lang_of(message.from_user.id)),
    )


# ============================================================
# MAIN
# ============================================================

async def main():
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is missing or invalid.")

    try:
        init_movie_db()
        logger.info("Movie database initialized.")
    except Exception:
        logger.exception("Could not initialize movie database")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(router)        # Main router
    dp.include_router(admin_router)  # Admin router

    await bot.delete_webhook(drop_pending_updates=False)
    logger.info("MovieBot started.")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MovieBot stopped.")
