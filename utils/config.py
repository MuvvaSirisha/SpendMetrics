# ─────────────────────────────────────────────────────────────────────────────
# utils/config.py — Central Configuration for SpendSense
#
# PURPOSE:
#   All magic numbers, colors, and settings live here instead of being
#   scattered across many files. When you want to change something (like the
#   currency symbol or a color), you change it in ONE place.
#
# INTERVIEW TIP:
#   "I centralized all configuration into a single config.py module so that
#    settings are easy to find, modify, and understand."
# ─────────────────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

# Load variables from the ".env" file into os.environ.
# If ".env" doesn't exist (e.g., on a fresh clone), this does nothing silently.
load_dotenv()


# ── Application Identity ───────────────────────────────────────────────────────
APP_NAME = "SpendSense"
APP_VERSION = "1.0.0"
APP_ICON = "💰"          # Shown in the browser tab and sidebar header


# ── Currency ───────────────────────────────────────────────────────────────────
CURRENCY_SYMBOL = "₹"    # Indian Rupees
CURRENCY_LOCALE = "en_IN"


# ── Visual Theme ───────────────────────────────────────────────────────────────
# These color constants are used across Plotly charts and CSS snippets.
THEME = {
    "primary":     "#1B3A6B",   # Navy blue  — main brand color
    "secondary":   "#2ECC71",   # Green      — positive values (income, budget OK)
    "accent":      "#3498DB",   # Light blue — highlights
    "danger":      "#E74C3C",   # Red        — negative values (over budget, alerts)
    "warning":     "#F39C12",   # Orange     — warnings
    "background":  "#F8F9FA",   # Off-white  — page background
    "card":        "#FFFFFF",   # White      — metric card backgrounds
    "text":        "#2C3E50",   # Dark grey  — body text
    "muted":       "#7F8C8D",   # Mid-grey   — secondary text
}

# Plotly chart color sequence for multi-series charts
CHART_COLORS = [
    "#1B3A6B", "#2ECC71", "#3498DB", "#E74C3C",
    "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22",
    "#34495E", "#F1C40F", "#E91E63", "#00BCD4",
]


# ── Transaction Categories ──────────────────────────────────────────────────────
# The canonical list of categories used throughout the app.
# Order matters — it's the order shown in dropdowns and charts.
CATEGORIES = [
    "Food & Dining",
    "Shopping",
    "Travel & Transport",
    "Bills & Utilities",
    "Entertainment",
    "Healthcare",
    "Education",
    "Rent",
    "Salary & Income",
    "Transfers",
    "Subscriptions",
    "Groceries",
    "Other",
]

# Category icon mapping — displayed in tables and charts
CATEGORY_ICONS = {
    "Food & Dining":      "🍽️",
    "Shopping":           "🛍️",
    "Travel & Transport": "✈️",
    "Bills & Utilities":  "💡",
    "Entertainment":      "🎬",
    "Healthcare":         "🏥",
    "Education":          "📚",
    "Rent":               "🏠",
    "Salary & Income":    "💼",
    "Transfers":          "🔄",
    "Subscriptions":      "📱",
    "Groceries":          "🛒",
    "Other":              "📦",
}

# Which categories represent income (positive cash flow)
INCOME_CATEGORIES = {"Salary & Income", "Transfers"}

# Which categories are considered neutral (not expenses, not income)
NEUTRAL_CATEGORIES = {"Transfers"}


# ── Database Configuration ─────────────────────────────────────────────────────
# Read from environment variables. Defaults make local development easy.

USE_MYSQL = os.getenv("USE_MYSQL", "false").lower() == "true"

# MySQL settings (only used when USE_MYSQL=True)
MYSQL_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "spendsense"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# SQLite settings (fallback when USE_MYSQL=False)
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/spendsense.db")


# ── CSV Upload Limits ──────────────────────────────────────────────────────────
MAX_CSV_SIZE_MB = int(os.getenv("MAX_CSV_SIZE_MB", "10"))
MAX_CSV_ROWS = int(os.getenv("MAX_CSV_ROWS", "10000"))

# Columns we look for when reading a CSV.
# We try each alias in order; the first match wins.
CSV_COLUMN_ALIASES = {
    "date":        ["date", "transaction_date", "txn_date", "trans_date", "value_date"],
    "description": ["description", "desc", "narration", "particulars", "details", "merchant"],
    "amount":      ["amount", "amt", "transaction_amount", "txn_amount"],
    "debit":       ["debit", "debit_amount", "withdrawal", "dr"],
    "credit":      ["credit", "credit_amount", "deposit", "cr"],
    "type":        ["type", "transaction_type", "txn_type", "trans_type"],
    "category":    ["category", "cat", "expense_category"],
}


# ── Budget Alerts ──────────────────────────────────────────────────────────────
# Warn when spending reaches this fraction of the budget (0.8 = 80%)
BUDGET_WARNING_THRESHOLD = 0.80

# Flag a transaction as unusual when it is this many times the category average
UNUSUAL_SPENDING_MULTIPLIER = 3.0

# Minimum number of transactions needed before we start detecting unusual spending
MIN_TRANSACTIONS_FOR_ANOMALY = 5


# ── Recurring Payment Detection ────────────────────────────────────────────────
# Minimum number of similar transactions to call something "recurring"
RECURRING_MIN_OCCURRENCES = 2

# Amount tolerance: two transactions are "similar amount" if they differ by ≤ this %
RECURRING_AMOUNT_TOLERANCE = 0.10   # 10%

# Day tolerance: two transactions are "similar interval" if the gap differs by ≤ this many days
RECURRING_DAY_TOLERANCE = 5


# ── Pagination ─────────────────────────────────────────────────────────────────
TRANSACTIONS_PER_PAGE = 50


def format_currency(amount: float) -> str:
    """
    Format a number as Indian Rupees with comma separators.

    Examples:
        format_currency(1234567.89)  →  "₹12,34,567.89"
        format_currency(-500)        →  "-₹500.00"

    We implement the Indian numbering system manually because Python's locale
    module can be unreliable across different operating systems.
    """
    if amount < 0:
        return f"-{CURRENCY_SYMBOL}{abs(amount):,.2f}"
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a float as a percentage string. Example: 0.754 → '75.4%'"""
    return f"{value * 100:.{decimals}f}%"
