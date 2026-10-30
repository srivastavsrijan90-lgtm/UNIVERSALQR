"""
UniversalQR Database Management Layer
Supports both MySQL and SQLite transparently with automatic fallback,
unified parameter formatting (%s -> ? for SQLite), dictionary-style results,
and non-destructive schema migrations.
"""

import os
import re
import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger("universal_qr.db")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "database.db")

# Read database configuration from environment
DB_TYPE_PREF = os.getenv("DB_TYPE", "").lower()  # "mysql" or "sqlite" or auto
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "1111")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "universal_qr")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

_ACTIVE_ENGINE = None  # "mysql" or "sqlite"

def detect_engine():
    global _ACTIVE_ENGINE
    if _ACTIVE_ENGINE:
        return _ACTIVE_ENGINE

    if DB_TYPE_PREF == "sqlite":
        _ACTIVE_ENGINE = "sqlite"
        logger.info("Using SQLite database by explicit DB_TYPE preference: %s", SQLITE_DB_PATH)
        return _ACTIVE_ENGINE

    # Try MySQL connection
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            port=MYSQL_PORT,
            connection_timeout=3
        )
        conn.close()
        _ACTIVE_ENGINE = "mysql"
        logger.info("Connected successfully to MySQL database '%s' at %s:%s", MYSQL_DATABASE, MYSQL_HOST, MYSQL_PORT)
        return _ACTIVE_ENGINE
    except Exception as e:
        logger.warning("Could not connect to MySQL (%s). Falling back to SQLite.", e)
        _ACTIVE_ENGINE = "sqlite"
        return _ACTIVE_ENGINE


class DatabaseSession:
    def __init__(self, engine, connection):
        self.engine = engine
        self.connection = connection

    def _prepare_sql(self, sql):
        if self.engine == "sqlite":
            # Convert standard %s placeholders to SQLite ? placeholders
            # Carefully avoiding %% or already formatted params
            return re.sub(r'(?<!%)%s', '?', sql)
        return sql

    def execute(self, sql, params=None):
        prepared_sql = self._prepare_sql(sql)
        params = params or ()
        if self.engine == "mysql":
            cursor = self.connection.cursor(dictionary=True, buffered=True)
            cursor.execute(prepared_sql, params)
            return cursor
        else:
            cursor = self.connection.cursor()
            cursor.execute(prepared_sql, params)
            return cursor

    def fetchall(self, sql, params=None):
        cursor = self.execute(sql, params)
        try:
            if self.engine == "mysql":
                rows = cursor.fetchall() or []
                return [dict(r) for r in rows]
            else:
                rows = cursor.fetchall() or []
                return [dict(r) for r in rows]
        finally:
            cursor.close()

    def fetchone(self, sql, params=None):
        cursor = self.execute(sql, params)
        try:
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            cursor.close()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


@contextmanager
def get_db():
    engine = detect_engine()
    if engine == "mysql":
        import mysql.connector
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            port=MYSQL_PORT,
            autocommit=False
        )
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row

    session = DatabaseSession(engine, conn)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_active_engine():
    return detect_engine()


def initialize_database():
    """Initializes tables and ensures all necessary columns exist for both MySQL and SQLite."""
    engine = detect_engine()
    with get_db() as db:
        if engine == "mysql":
            db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    user_code VARCHAR(20) UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    avatar VARCHAR(500) NULL,
                    avatar_color VARCHAR(20) DEFAULT '#5b5ce2',
                    bio TEXT NULL,
                    phone VARCHAR(50) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS universal_profiles (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NULL,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    description TEXT,
                    photo VARCHAR(500),
                    custom_fields LONGTEXT,
                    qr_code VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Run column checks and migrations for MySQL
            cols_users = {row["COLUMN_NAME"] for row in db.fetchall(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'",
                (MYSQL_DATABASE,)
            )}
            if "user_code" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN user_code VARCHAR(20) UNIQUE NULL;")
            if "avatar" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN avatar VARCHAR(500) NULL;")
            if "avatar_color" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN avatar_color VARCHAR(20) DEFAULT '#5b5ce2';")
            if "bio" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN bio TEXT NULL;")
            if "phone" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(50) NULL;")

            cols_profiles = {row["COLUMN_NAME"] for row in db.fetchall(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'universal_profiles'",
                (MYSQL_DATABASE,)
            )}
            if "user_id" not in cols_profiles:
                db.execute("ALTER TABLE universal_profiles ADD COLUMN user_id VARCHAR(36) NULL;")
            if "updated_at" not in cols_profiles:
                db.execute("ALTER TABLE universal_profiles ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        else:
            # SQLite setup
            db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    user_code TEXT UNIQUE,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    avatar TEXT,
                    avatar_color TEXT DEFAULT '#5b5ce2',
                    bio TEXT,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS universal_profiles (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    photo TEXT DEFAULT '',
                    custom_fields TEXT DEFAULT '[]',
                    qr_code TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Run column migrations for SQLite
            cols_users = {row["name"] for row in db.fetchall("PRAGMA table_info(users)")}
            if "user_code" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN user_code TEXT;")
            if "avatar" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN avatar TEXT;")
            if "avatar_color" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN avatar_color TEXT DEFAULT '#5b5ce2';")
            if "bio" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN bio TEXT;")
            if "phone" not in cols_users:
                db.execute("ALTER TABLE users ADD COLUMN phone TEXT;")

            cols_profiles = {row["name"] for row in db.fetchall("PRAGMA table_info(universal_profiles)")}
            if "user_id" not in cols_profiles:
                db.execute("ALTER TABLE universal_profiles ADD COLUMN user_id TEXT;")
            if "updated_at" not in cols_profiles:
                db.execute("ALTER TABLE universal_profiles ADD COLUMN updated_at TIMESTAMP NULL;")

        # Populate user_code for existing users if missing
        users_without_code = db.fetchall("SELECT id, name FROM users WHERE user_code IS NULL OR user_code = ''")
        for u in users_without_code:
            import random
            import string
            code = "UQR-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            db.execute("UPDATE users SET user_code = %s WHERE id = %s", (code, u["id"]))

        # For any profiles with NULL user_id, if there is a user, associate them with the first user
        first_user = db.fetchone("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
        if first_user:
            db.execute("UPDATE universal_profiles SET user_id = %s WHERE user_id IS NULL OR user_id = ''", (first_user["id"],))

    logger.info("UniversalQR database initialized successfully using %s engine.", engine.upper())
