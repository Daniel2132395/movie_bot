# ============================================================
# MovieBot - Movie Database
# SQLite database for storing movie information
# ============================================================

import sqlite3
from pathlib import Path
from typing import Optional

# ============================================================
# DATABASE CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "movies.db"


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    """Create a SQLite connection."""
    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    return connection


# ============================================================
# INIT DATABASE
# ============================================================

def init_movie_db():
    """Create database and movies table if they don't exist."""
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tmdb_id INTEGER UNIQUE,
                title TEXT NOT NULL,
                original_title TEXT,
                year INTEGER,
                overview TEXT,
                poster_path TEXT,
                vote_average REAL DEFAULT 0,
                vote_count INTEGER DEFAULT 0,
                imdb_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_movies_tmdb_id ON movies(tmdb_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title)
        """)

        connection.commit()
    finally:
        connection.close()


# ============================================================
# SAVE MOVIE
# ============================================================

def save_movie(movie: dict):
    """Save or update a movie in the database."""
    tmdb_id = movie.get("id")
    if not tmdb_id:
        return None

    title = movie.get("title") or movie.get("name") or movie.get("original_title") or "Unknown"
    original_title = movie.get("original_title") or movie.get("original_name")
    release_date = movie.get("release_date") or movie.get("first_air_date") or ""

    try:
        year = int(release_date[:4])
    except (ValueError, TypeError):
        year = None

    overview = movie.get("overview")
    poster_path = movie.get("poster_path")
    vote_average = movie.get("vote_average", 0)
    vote_count = movie.get("vote_count", 0)
    imdb_id = movie.get("imdb_id")

    connection = get_connection()
    try:
        connection.execute("""
            INSERT INTO movies (
                tmdb_id, title, original_title, year, overview,
                poster_path, vote_average, vote_count, imdb_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tmdb_id) DO UPDATE SET
                title = excluded.title,
                original_title = excluded.original_title,
                year = excluded.year,
                overview = excluded.overview,
                poster_path = excluded.poster_path,
                vote_average = excluded.vote_average,
                vote_count = excluded.vote_count,
                imdb_id = excluded.imdb_id,
                updated_at = CURRENT_TIMESTAMP
        """, (
            tmdb_id, title, original_title, year, overview,
            poster_path, vote_average, vote_count, imdb_id
        ))

        connection.commit()
        row = connection.execute(
            "SELECT * FROM movies WHERE tmdb_id = ?",
            (tmdb_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


# ============================================================
# GET MOVIE
# ============================================================

def get_movie(tmdb_id: int) -> Optional[dict]:
    """Get a movie by TMDb ID."""
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM movies WHERE tmdb_id = ?",
            (tmdb_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


# ============================================================
# SEARCH LOCAL
# ============================================================

def search_local_movies(query: str, limit: int = 10):
    """Search movies in local database."""
    query = query.strip()
    if not query:
        return []

    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT * FROM movies
            WHERE title LIKE ? OR original_title LIKE ?
            ORDER BY vote_average DESC, vote_count DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


# ============================================================
# DELETE MOVIE
# ============================================================

def delete_movie(tmdb_id: int) -> bool:
    """Delete a movie from database."""
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM movies WHERE tmdb_id = ?",
            (tmdb_id,)
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


# ============================================================
# COUNT
# ============================================================

def movie_count() -> int:
    """Return number of stored movies."""
    connection = get_connection()
    try:
        row = connection.execute("SELECT COUNT(*) AS total FROM movies").fetchone()
        return int(row["total"])
    finally:
        connection.close()


# ============================================================
# CLEAR
# ============================================================

def clear_movies():
    """Delete all movies."""
    connection = get_connection()
    try:
        connection.execute("DELETE FROM movies")
        connection.commit()
    finally:
        connection.close()


# ============================================================
# AUTO INIT
# ============================================================

init_movie_db()
