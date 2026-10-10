# ─────────────────────────────────────────────────────────────────────────────
# database/connection.py — Database Connection Manager
#
# PURPOSE:
#   This module is the ONLY place in the project that knows how to connect
#   to the database. Every other module calls get_connection() from here.
#
# DESIGN DECISION — Why one connection module?
#   If we ever switch from SQLite to MySQL (or vice versa), we only change
#   THIS file. All other files keep working without modification.
#
# HOW IT WORKS:
#   1. We read USE_MYSQL from config.py (which reads from .env)
#   2. If USE_MYSQL=True  → connect to MySQL using mysql-connector-python
#   3. If USE_MYSQL=False → connect to SQLite using Python's built-in sqlite3
#
# INTERVIEW TIP:
#   "I used the Adapter pattern here — get_connection() returns a connection
#    object that behaves the same way whether it's SQLite or MySQL, so the
#    rest of the code doesn't need to know which database is being used."
# ─────────────────────────────────────────────────────────────────────────────

import sqlite3
import os
from utils.config import USE_MYSQL, MYSQL_CONFIG, SQLITE_DB_PATH


def get_connection():
    """
    Return a database connection — either SQLite or MySQL depending on config.

    Usage:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions")
        conn.close()

    IMPORTANT:
        Always close the connection after use to free resources.
        Or use a context manager: `with get_connection() as conn:`
    """
    if USE_MYSQL:
        return _get_mysql_connection()
    else:
        return _get_sqlite_connection()


def _get_sqlite_connection():
    """
    Connect to the local SQLite database file.

    SQLite stores everything in a single .db file — no server needed.
    Python's built-in sqlite3 module handles it.

    IMPORTANT:
        check_same_thread=False is required when Streamlit reruns the script
        on a different thread. SQLite normally restricts connections to the
        thread that created them; this disables that restriction.
    """
    # Make sure the data/ directory exists before creating the file
    db_dir = os.path.dirname(SQLITE_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)

    # Row factory: makes rows behave like dictionaries instead of plain tuples.
    # This lets us write row["amount"] instead of row[3].
    conn.row_factory = sqlite3.Row

    # Enable foreign key enforcement (SQLite disables this by default)
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def _get_mysql_connection():
    """
    Connect to a MySQL server using credentials from config.py / .env file.

    Raises a clear error if the connection fails, so the user sees a helpful
    message instead of a cryptic stack trace.
    """
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            database=MYSQL_CONFIG["database"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            autocommit=False,
        )
        return conn
    except ImportError:
        raise RuntimeError(
            "mysql-connector-python is not installed. "
            "Run: pip install mysql-connector-python"
        )
    except Exception as e:
        raise RuntimeError(
            f"Could not connect to MySQL.\n"
            f"Host: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}\n"
            f"Database: {MYSQL_CONFIG['database']}\n"
            f"Error: {e}\n\n"
            f"Tip: Set USE_MYSQL=false in your .env file to use SQLite instead."
        )


def test_connection() -> tuple[bool, str]:
    """
    Try to connect to the database and return (success, message).

    Used by the Settings page to show the connection status.

    Returns:
        (True, "Connected to SQLite at data/spendsense.db")
        (False, "Could not connect: ...")
    """
    try:
        conn = get_connection()
        if USE_MYSQL:
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            conn.close()
            return True, f"Connected to MySQL {version} at {MYSQL_CONFIG['host']}"
        else:
            conn.close()
            return True, f"Connected to SQLite at {SQLITE_DB_PATH}"
    except Exception as e:
        return False, str(e)


def get_db_type() -> str:
    """Return 'SQLite' or 'MySQL' — used for display purposes."""
    return "MySQL" if USE_MYSQL else "SQLite"
