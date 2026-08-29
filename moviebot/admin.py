# admin.py
# ============================================================
# MOVIEBOT PROFESSIONAL ADMIN PANEL
# Compatible with aiogram 3.x
# ============================================================

import sqlite3
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# ============================================================
# CONFIG
# ============================================================

OWNER_ID = 8960475306

DB_NAME = "admin.db"

admin_router = Router()


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(
        DB_NAME,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_admin_db():

    conn = get_db()
    cur = conn.cursor()

    # --------------------------------------------------------
    # ADMINS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # USAGE
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # SEARCHES
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            search_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # Make sure OWNER exists
    # --------------------------------------------------------

    cur.execute(
        "SELECT user_id FROM admins WHERE user_id = ?",
        (OWNER_ID,),
    )

    if cur.fetchone() is None:

        cur.execute(
            """
            INSERT INTO admins
            (user_id, added_by, created_at)
            VALUES (?, ?, ?)
            """,
            (
                OWNER_ID,
                OWNER_ID,
                now(),
            ),
        )

    conn.commit()
    conn.close()


# ============================================================
# TIME
# ============================================================

def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def utc_day_start():
    dt = datetime.now(timezone.utc).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    return dt.isoformat()


# ============================================================
# USER TRACKING
# ============================================================

async def track_user(user):

    if user is None:
        return

    user_id = user.id

    username = user.username or ""
    first_name = user.first_name or ""

    current_time = now()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,),
    )

    exists = cur.fetchone()

    if exists:

        cur.execute(
            """
            UPDATE users
            SET username = ?,
                first_name = ?,
                last_seen = ?
            WHERE user_id = ?
            """,
            (
                username,
                first_name,
                current_time,
                user_id,
            ),
        )

    else:

        cur.execute(
            """
            INSERT INTO users
            (
                user_id,
                username,
                first_name,
                created_at,
                last_seen
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                first_name,
                current_time,
                current_time,
            ),
        )

    conn.commit()
    conn.close()


# ============================================================
# USAGE TRACKING
# ============================================================

async def track_usage(
    user_id: int,
    action: str,
):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO usage
        (
            user_id,
            action,
            created_at
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            action,
            now(),
        ),
    )

    conn.commit()
    conn.close()


# ============================================================
# SEARCH TRACKING
# ============================================================

async def track_search(
    user_id: int,
    search_type: str,
):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO searches
        (
            user_id,
            search_type,
            created_at
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            search_type,
            now(),
        ),
    )

    conn.commit()
    conn.close()

    await track_usage(
        user_id,
        f"search:{search_type}",
    )


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(user_id: int) -> bool:

    if user_id == OWNER_ID:
        return True

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id FROM admins WHERE user_id = ?",
        (user_id,),
    )

    result = cur.fetchone()

    conn.close()

    return result is not None


def is_owner(user_id: int) -> bool:

    return user_id == OWNER_ID


# ============================================================
# KEYBOARDS
# ============================================================

def admin_main_kb():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 آمار کلی",
                    callback_data="admin:stats",
                ),
                InlineKeyboardButton(
                    text="📈 آمار زمانی",
                    callback_data="admin:time_stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 کاربران",
                    callback_data="admin:users",
                ),
                InlineKeyboardButton(
                    text="👑 مدیریت ادمین‌ها",
                    callback_data="admin:admins",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 بروزرسانی",
                    callback_data="admin:refresh",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ بستن پنل",
                    callback_data="admin:close",
                ),
            ],
        ]
    )


def admin_management_kb():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن ادمین",
                    callback_data="admin:add",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 حذف ادمین",
                    callback_data="admin:remove",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 لیست ادمین‌ها",
                    callback_data="admin:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin:home",
                ),
            ],
        ]
    )


def back_admin_kb():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به پنل",
                    callback_data="admin:home",
                )
            ]
        ]
    )


# ============================================================
# ADMIN STATE
# ============================================================

class AdminState(StatesGroup):

    waiting_add_id = State()
    waiting_remove_id = State()


# ============================================================
# /admin
# ============================================================

@admin_router.message(Command("admin"))
async def admin_command(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id

    if not is_admin(user_id):

        await message.answer(
            "⛔ شما اجازه دسترسی به پنل مدیریت را ندارید."
        )

        return

    await state.clear()

    await message.answer(
        "🎬 <b>MovieBot Admin Panel</b>\n\n"
        "خوش آمدید مدیر عزیز 👑\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=admin_main_kb(),
    )


# ============================================================
# HOME
# ============================================================

@admin_router.callback_query(
    F.data == "admin:home"
)
async def admin_home(
    call: CallbackQuery,
    state: FSMContext,
):

    if not is_admin(call.from_user.id):

        await call.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    await state.clear()

    await call.message.edit_text(
        "🎬 <b>MovieBot Admin Panel</b>\n\n"
        "مدیریت حرفه‌ای ربات:",
        reply_markup=admin_main_kb(),
    )

    await call.answer()


# ============================================================
# GENERAL STATS
# ============================================================

@admin_router.callback_query(
    F.data == "admin:stats"
)
async def admin_stats(
    call: CallbackQuery,
):

    if not is_admin(call.from_user.id):

        await call.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    conn = get_db()
    cur = conn.cursor()

    # Users
    cur.execute(
        "SELECT COUNT(*) AS c FROM users"
    )
    total_users = cur.fetchone()["c"]

    # Searches
    cur.execute(
        "SELECT COUNT(*) AS c FROM searches"
    )
    total_searches = cur.fetchone()["c"]

    # Usage
    cur.execute(
        "SELECT COUNT(*) AS c FROM usage"
    )
    total_usage = cur.fetchone()["c"]

    # Admins
    cur.execute(
        "SELECT COUNT(*) AS c FROM admins"
    )
    total_admins = cur.fetchone()["c"]

    # Today users
    start = utc_day_start()

    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM users
        WHERE created_at >= ?
        """,
        (start,),
    )

    new_today = cur.fetchone()["c"]

    # Active today
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM users
        WHERE last_seen >= ?
        """,
        (start,),
    )

    active_today = cur.fetchone()["c"]

    conn.close()

    text = (
        "📊 <b>آمار کلی MovieBot</b>\n\n"

        f"👥 کل کاربران: <b>{total_users:,}</b>\n"
        f"🆕 کاربران جدید امروز: <b>{new_today:,}</b>\n"
        f"🟢 کاربران فعال امروز: <b>{active_today:,}</b>\n\n"

        f"🔎 کل جستجوها: <b>{total_searches:,}</b>\n"
        f"⚡ کل استفاده‌ها: <b>{total_usage:,}</b>\n\n"

        f"👑 تعداد ادمین‌ها: <b>{total_admins:,}</b>"
    )

    await call.message.edit_text(
        text,
        reply_markup=back_admin_kb(),
    )

    await call.answer()


# ============================================================
# TIME STATS
# ============================================================

@admin_router.callback_query(
    F.data == "admin:time_stats"
)
async def admin_time_stats(
    call: CallbackQuery,
):

    if not is_admin(call.from_user.id):

        await call.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    conn = get_db()
    cur = conn.cursor()

    now_dt = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # TODAY
    # --------------------------------------------------------

    today = now_dt.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ).isoformat()

    # --------------------------------------------------------
    # 7 DAYS
    # --------------------------------------------------------

    week = (
        now_dt - timedelta(days=7)
    ).isoformat()

    # --------------------------------------------------------
    # 30 DAYS
    # --------------------------------------------------------

    month = (
        now_dt - timedelta(days=30)
    ).isoformat()

    # Users
    cur.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE created_at >= ?
        """,
        (today,),
    )

    users_today = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE created_at >= ?
        """,
        (week,),
    )

    users_week = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE created_at >= ?
        """,
        (month,),
    )

    users_month = cur.fetchone()[0]

    # Searches
    cur.execute(
        """
        SELECT COUNT(*)
        FROM searches
        WHERE created_at >= ?
        """,
        (today,),
    )

    searches_today = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*)
        FROM searches
        WHERE created_at >= ?
        """,
        (week,),
    )

    searches_week = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*)
        FROM searches
        WHERE created_at >= ?
        """,
        (month,),
    )

    searches_month = cur.fetchone()[0]

    conn.close()

    text = (
        "📈 <b>آمار زمانی MovieBot</b>\n\n"

        "📅 <b>امروز</b>\n"
        f"👥 کاربران جدید: {users_today:,}\n"
        f"🔎 جستجوها: {searches_today:,}\n\n"

        "📆 <b>۷ روز اخیر</b>\n"
        f"👥 کاربران جدید: {users_week:,}\n"
        f"🔎 جستجوها: {searches_week:,}\n\n"

        "🗓 <b>۳۰ روز اخیر</b>\n"
        f"👥 کاربران جدید: {users_month:,}\n"
        f"🔎 جستجوها: {searches_month:,}"
    )

    await call.message.edit_text(
        text,
        reply_markup=back_admin_kb(),
    )

    await call.answer()


# ============================================================
# USERS
# ============================================================

@admin_router.callback_query(
    F.data == "admin:users"
)
async def admin_users(
    call: CallbackQuery,
):

    if not is_admin(call.from_user.id):

        await call.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            user_id,
            username,
            first_name,
            last_seen
        FROM users
        ORDER BY last_seen DESC
        LIMIT 15
        """
    )

    rows = cur.fetchall()

    conn.close()

    if not rows:

        text = "👥 هنوز کاربری ثبت نشده است."

    else:

        lines = [
            "👥 <b>آخرین کاربران MovieBot</b>\n"
        ]

        for i, row in enumerate(rows, 1):

            username = (
                f"@{row['username']}"
                if row["username"]
                else "بدون username"
            )

            first_name = (
                row["first_name"]
                or "بدون نام"
            )

            lines.append(
                f"{i}. {first_name}\n"
                f"   🆔 {row['user_id']}\n"
                f"   👤 {username}\n"
            )

        text = "\n".join(lines)

    await call.message.edit_text(
        text[:4090],
        reply_markup=back_admin_kb(),
    )

    await call.answer()


# ============================================================
# ADMIN MANAGEMENT
# ============================================================

@admin_router.callback_query(
    F.data == "admin:admins"
)
async def admin_management(
    call: CallbackQuery,
):

    if not is_admin(call.from_user.id):

        await call.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    await call.message.edit_text(
        "👑 <b>مدیریت ادمین‌ها</b>\n\n"
        "از گزینه‌های زیر استفاده کنید:",
        reply_markup=admin_management_kb(),
    )

    await call.answer()


# ============================================================
# LIST ADMINS
# ============================================================

@admin_router.callback_query(
    F.data == "admin:list"
)
async def admin_list(
    call: CallbackQuery,
):

    if not is_admin(call.from_user.id):

        await call.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT user_id, added_by, created_at
        FROM admins
        ORDER BY created_at ASC
        """
    )

    rows = cur.fetchall()

    conn.close()

    lines = [
        "👑 <b>لیست مدیران MovieBot</b>\n"
    ]

    for i, row in enumerate(rows, 1):

        if row["user_id"] == OWNER_ID:

            role = "👑 Owner"

        else:

            role = "🛡 Admin"

        lines.append(
            f"{i}. {role}\n"
            f"🆔 <code>{row['user_id']}</code>\n"
        )

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=back_admin_kb(),
    )

    await call.answer()


# ============================================================
# ADD ADMIN
# ============================================================

@admin_router.callback_query(
    F.data == "admin:add"
)
async def admin_add_start(
    call: CallbackQuery,
    state: FSMContext,
):

    if not is_owner(call.from_user.id):

        await call.answer(
            "⛔ فقط Owner می‌تواند ادمین اضافه کند.",
            show_alert=True,
        )

        return

    await state.set_state(
        AdminState.waiting_add_id
    )

    await call.message.edit_text(
        "➕ <b>افزودن ادمین</b>\n\n"
        "Telegram ID شخص را ارسال کن.\n\n"
        "مثال:\n"
        "<code>123456789</code>\n\n"
        "برای لغو /cancel را بفرست.",
    )

    await call.answer()


@admin_router.message(
    AdminState.waiting_add_id
)
async def admin_add_finish(
    message: Message,
    state: FSMContext,
):

    if not is_owner(message.from_user.id):

        await state.clear()

        return

    raw = message.text.strip()

    if not raw.isdigit():

        await message.answer(
            "❌ Telegram ID باید فقط شامل عدد باشد.\n\n"
            "مثال:\n"
            "<code>123456789</code>"
        )

        return

    new_admin_id = int(raw)

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id FROM admins WHERE user_id = ?",
        (new_admin_id,),
    )

    exists = cur.fetchone()

    if exists:

        conn.close()

        await state.clear()

        await message.answer(
            "⚠️ این شخص از قبل ادمین است.",
            reply_markup=admin_main_kb(),
        )

        return

    cur.execute(
        """
        INSERT INTO admins
        (
            user_id,
            added_by,
            created_at
        )
        VALUES (?, ?, ?)
        """,
        (
            new_admin_id,
            message.from_user.id,
            now(),
        ),
    )

    conn.commit()
    conn.close()

    await state.clear()

    await message.answer(
        "✅ <b>ادمین با موفقیت اضافه شد.</b>\n\n"
        f"🆔 ID: <code>{new_admin_id}</code>\n\n"
        "اکنون این شخص می‌تواند با دستور /admin "
        "وارد پنل شود.",
        reply_markup=admin_main_kb(),
    )


# ============================================================
# REMOVE ADMIN
# ============================================================

@admin_router.callback_query(
    F.data == "admin:remove"
)
async def admin_remove_start(
    call: CallbackQuery,
    state: FSMContext,
):

    if not is_owner(call.from_user.id):

        await call.answer(
            "⛔ فقط Owner می‌تواند ادمین حذف کند.",
            show_alert=True,
        )

        return

    await state.set_state(
        AdminState.waiting_remove_id
    )

    await call.message.edit_text(
        "🗑 <b>حذف ادمین</b>\n\n"
        "Telegram ID ادمینی که می‌خواهی حذف شود را بفرست.\n\n"
        "⚠️ Owner قابل حذف نیست."
    )

    await call.answer()


@admin_router.message(
    AdminState.waiting_remove_id
)
async def admin_remove_finish(
    message: Message,
    state: FSMContext,
):

    if not is_owner(message.from_user.id):

        await state.clear()

        return

    raw = message.text.strip()

    if not raw.isdigit():

        await message.answer(
            "❌ ID نامعتبر است."
        )

        return

    remove_id = int(raw)

    if remove_id == OWNER_ID:

        await state.clear()

        await message.answer(
            "⛔ Owner اصلی قابل حذف نیست.",
            reply_markup=admin_main_kb(),
        )

        return

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM admins WHERE user_id = ?",
        (remove_id,),
    )

    deleted = cur.rowcount

    conn.commit()
    conn.close()

    await state.clear()

    if deleted:

        text = (
            "✅ <b>ادمین حذف شد.</b>\n\n"
            f"🆔 ID: <code>{remove_id}</code>"
        )

    else:

        text = (
            "⚠️ این ID در لیست ادمین‌ها وجود نداشت."
        )

    await message.answer(
        text,
        reply_markup=admin_main_kb(),
    )


# ============================================================
# REFRESH
# ============================================================

@admin_router.callback_query(
    F.data == "admin:refresh"
)
async def admin_refresh(
    call: CallbackQuery,
):

    if not is_admin(call.from_user.id):

        await call.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    await call.answer(
        "✅ آمار بروزرسانی شد."
    )

    await call.message.edit_text(
        "🎬 <b>MovieBot Admin Panel</b>\n\n"
        "📊 اطلاعات آماده است.",
        reply_markup=admin_main_kb(),
    )


# ============================================================
# CLOSE
# ============================================================

@admin_router.callback_query(
    F.data == "admin:close"
)
async def admin_close(
    call: CallbackQuery,
    state: FSMContext,
):

    if not is_admin(call.from_user.id):

        await call.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    await state.clear()

    await call.message.delete()

    await call.answer(
        "پنل بسته شد."
    )


# ============================================================
# CANCEL
# ============================================================

@admin_router.message(
    Command("cancel"),
    AdminState.waiting_add_id,
)
async def cancel_add(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await message.answer(
        "❌ عملیات لغو شد.",
        reply_markup=admin_main_kb(),
    )


@admin_router.message(
    Command("cancel"),
    AdminState.waiting_remove_id,
)
async def cancel_remove(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    await message.answer(
        "❌ عملیات لغو شد.",
        reply_markup=admin_main_kb(),
    )
