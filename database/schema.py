# ─────────────────────────────────────────────────────────────────────────────
# database/schema.py — Database Schema (Table Definitions)
#
# PURPOSE:
#   This file defines the shape of the database — what tables exist,
#   what columns they have, and what constraints apply.
#
#   The function initialize_database() is called ONCE when the app starts.
#   It creates all tables if they don't already exist (IF NOT EXISTS means
#   it's safe to call multiple times without wiping your data).
#
# DATABASE DESIGN EXPLANATION:
#
#   transactions   — the central table; every row is one bank transaction
#   categories     — lookup table for category names (normalized design)
#   budgets        — monthly budget amounts per category
#   import_history — records each CSV file import for audit trail
#
# NORMALIZATION:
#   Instead of storing "Food & Dining" as a text string in every transaction
#   row, we store a category_id (a number). The actual name lives once in
#   the categories table. This is called "normalization" — it saves space
#   and prevents typos.
#
# INTERVIEW TIP:
#   "I used IF NOT EXISTS on CREATE TABLE so the function is idempotent —
#    it's safe to call on every app startup without losing existing data."
# ─────────────────────────────────────────────────────────────────────────────

from database.connection import get_connection, get_db_type
from utils.config import CATEGORIES


def initialize_database():
    """
    Create all database tables if they don't exist yet.
    Also seeds the categories lookup table with our standard category list.
    Called once when the Streamlit app starts.
    """
    conn = get_connection()
    try:
        _create_tables(conn)
        _seed_categories(conn)
        conn.commit()
    finally:
        conn.close()


def _create_tables(conn):
    """Create all tables. Safe to call even if tables already exist."""
    cursor = conn.cursor()
    db_type = get_db_type()

    # ── categories table ──────────────────────────────────────────────────────
    # Lookup table — maps a category ID to a category name.
    # PRIMARY KEY AUTOINCREMENT: the database assigns IDs automatically.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            icon        TEXT    DEFAULT '',
            is_income   INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── transactions table ────────────────────────────────────────────────────
    # The main table. Each row = one bank transaction.
    #
    # amount convention:
    #   Positive number = money IN  (income, refund, credit)
    #   Negative number = money OUT (expense, debit)
    #
    # category_id REFERENCES categories(id):
    #   This is a FOREIGN KEY — it ensures every category_id in transactions
    #   actually exists in the categories table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT   NOT NULL,
            description     TEXT    NOT NULL,
            amount          REAL    NOT NULL,
            transaction_type TEXT   DEFAULT 'debit',
            category_id     INTEGER REFERENCES categories(id),
            category_name   TEXT    DEFAULT 'Other',
            notes           TEXT    DEFAULT '',
            import_id       INTEGER,
            is_duplicate    INTEGER DEFAULT 0,
            created_at      TEXT    DEFAULT (datetime('now')),
            updated_at      TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── budgets table ─────────────────────────────────────────────────────────
    # One row per (category, month). amount = the budget limit in rupees.
    # UNIQUE(category_name, month_year) prevents duplicate budgets for the
    # same category and month.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name   TEXT    NOT NULL,
            month_year      TEXT    NOT NULL,
            amount          REAL    NOT NULL CHECK(amount > 0),
            created_at      TEXT    DEFAULT (datetime('now')),
            updated_at      TEXT    DEFAULT (datetime('now')),
            UNIQUE(category_name, month_year)
        )
    """)

    # ── import_history table ──────────────────────────────────────────────────
    # Tracks every CSV import. Useful for:
    #   - Showing the user what they've imported
    #   - Detecting duplicate imports
    #   - Audit trail
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            filename        TEXT    NOT NULL,
            imported_at     TEXT    DEFAULT (datetime('now')),
            row_count       INTEGER DEFAULT 0,
            accepted_count  INTEGER DEFAULT 0,
            rejected_count  INTEGER DEFAULT 0,
            duplicate_count INTEGER DEFAULT 0,
            source          TEXT    DEFAULT 'csv'
        )
    """)

    # ── INDEX: Speed up common queries ────────────────────────────────────────
    # Without an index, every query scans the entire table row by row.
    # An index on transaction_date means "find October transactions" is fast.
    #
    # CREATE INDEX IF NOT EXISTS = safe to run multiple times
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_date
        ON transactions(transaction_date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_category
        ON transactions(category_name)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_budgets_month
        ON budgets(month_year)
    """)


def _seed_categories(conn):
    """
    Insert the standard categories into the categories table.
    Uses INSERT OR IGNORE so we don't crash if they already exist.

    INSERT OR IGNORE:
        If a row with the same UNIQUE value (name) already exists,
        skip it silently instead of raising an error.
    """
    cursor = conn.cursor()
    from utils.config import CATEGORY_ICONS, INCOME_CATEGORIES

    for cat_name in CATEGORIES:
        icon = CATEGORY_ICONS.get(cat_name, "📦")
        is_income = 1 if cat_name in INCOME_CATEGORIES else 0
        cursor.execute(
            """
            INSERT OR IGNORE INTO categories (name, icon, is_income)
            VALUES (?, ?, ?)
            """,
            (cat_name, icon, is_income),
        )


def drop_all_tables():
    """
    Drop all tables. Used in Settings → "Clear All Data".
    WARNING: This permanently deletes everything.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS transactions")
        cursor.execute("DROP TABLE IF EXISTS budgets")
        cursor.execute("DROP TABLE IF EXISTS import_history")
        cursor.execute("DROP TABLE IF EXISTS categories")
        conn.commit()
    finally:
        conn.close()


def get_table_stats() -> dict:
    """
    Return row counts for each table. Used on the Settings page.
    Example return: {'transactions': 90, 'categories': 13, 'budgets': 3}
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        stats = {}
        for table in ["transactions", "categories", "budgets", "import_history"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except Exception:
                stats[table] = 0
        return stats
    finally:
        conn.close()
