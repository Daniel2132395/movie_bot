# ============================================================
# MOVIEBOT ADMIN PANEL
# Compatible with aiogram 3.x
# ============================================================

import sqlite3
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ============================================================
# CONFIG
# ============================================================

OWNER_ID = 8960475306  # ← آی‌دی خودتون رو اینجا بذارید

DB_NAME = "admin.db"
admin_router = Router()


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now(timezone.utc).isoformat()


def utc_day_start():
    dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return dt.isoformat()


def init_admin_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            search_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Make sure OWNER exists
    cur.execute("SELECT user_id FROM admins WHERE user_id = ?", (OWNER_ID,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO admins (user_id, added_by, created_at) VALUES (?, ?, ?)",
                   (OWNER_ID, OWNER_ID, now()))

    conn.commit()
    conn.close()


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


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
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = cur.fetchone()

    if exists:
        cur.execute("UPDATE users SET username = ?, first_name = ?, last_seen = ? WHERE user_id = ?",
                   (username, first_name, current_time, user_id))
    else:
        cur.execute("INSERT INTO users (user_id, username, first_name, created_at, last_seen) VALUES (?, ?, ?, ?, ?)",
                   (user_id, username, first_name, current_time, current_time))

    conn.commit()
    conn.close()


# ============================================================
# KEYBOARDS
# ============================================================

def admin_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار کلی", callback_data="admin:stats"),
         InlineKeyboardButton(text="📈 آمار زمانی", callback_data="admin:time_stats")],
        [InlineKeyboardButton(text="👥 کاربران", callback_data="admin:users"),
         InlineKeyboardButton(text="👑 مدیریت ادمین‌ها", callback_data="admin:admins")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="admin:refresh")],
        [InlineKeyboardButton(text="❌ بستن پنل", callback_data="admin:close")],
    ])


def admin_management_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ افزودن ادمین", callback_data="admin:add")],
        [InlineKeyboardButton(text="🗑 حذف ادمین", callback_data="admin:remove")],
        [InlineKeyboardButton(text="📋 لیست ادمین‌ها", callback_data="admin:list")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:home")],
    ])


def back_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="
