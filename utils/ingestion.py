# ─────────────────────────────────────────────────────────────────────────────
# utils/ingestion.py — CSV Reading, Validation, and Data Loading
#
# PURPOSE:
#   This module handles everything between "user uploads a CSV" and
#   "data is safely stored in the database". It:
#       1. Reads the CSV into a Pandas DataFrame
#       2. Detects and maps column names (even if they differ from expected)
#       3. Validates each row (dates, amounts, required fields)
#       4. Applies sign conventions (debit = negative, credit = positive)
#       5. Detects duplicates against existing database records
#       6. Returns clean data + a validation report
#
# SIGN CONVENTION (important!):
#   We store ALL amounts as signed numbers:
#       Expense / Debit  →  negative  (e.g. -450.00)
#       Income  / Credit →  positive  (e.g. 65000.00)
#   This makes SQL aggregation simple: SUM(amount) = net cash flow.
#
# INTERVIEW TIP:
#   "I separated data ingestion from UI code so the same validation
#    logic works whether the user uploads a file or we load sample data.
#    I also separated validation from insertion — a common industry pattern
#    called Extract-Transform-Load (ETL)."
# ─────────────────────────────────────────────────────────────────────────────

import io
import os
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil import parser as dateutil_parser

from utils.config import (
    CSV_COLUMN_ALIASES,
    MAX_CSV_SIZE_MB,
    MAX_CSV_ROWS,
    CATEGORIES,
)
from utils.categorization import categorize_transaction


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Column Detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """
    Map standard column names to actual column names in the uploaded CSV.

    WHY THIS IS NEEDED:
        Banks export CSVs with different column names:
            - SBI uses "Narration", HDFC uses "Description"
            - Some use "Debit Amount" / "Credit Amount" instead of "Amount"
        We try a list of known aliases for each standard column name.

    Returns:
        A dict like: {'date': 'Transaction Date', 'amount': 'Amount', ...}
        Value is None if no matching column was found.

    Example:
        CSV has columns: ['Trans Date', 'Narration', 'Withdrawal']
        Returns: {'date': 'Trans Date', 'description': 'Narration',
                  'amount': None, 'debit': 'Withdrawal', ...}
    """
    # Normalize: lowercase all column names for case-insensitive matching
    col_map_lower = {col.lower().strip(): col for col in df.columns}
    detected = {}

    for standard_name, aliases in CSV_COLUMN_ALIASES.items():
        found = None
        for alias in aliases:
            if alias.lower() in col_map_lower:
                found = col_map_lower[alias.lower()]
                break
        detected[standard_name] = found

    return detected


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Validation Helpers
# ─────────────────────────────────────────────────────────────────────────────

def parse_date(value) -> str | None:
    """
    Try to parse a date value into 'YYYY-MM-DD' format.

    We use dateutil.parser which understands many formats:
        '15/09/2024', '2024-09-15', '15 Sep 2024', 'Sep 15, 2024', etc.

    Returns None if the value cannot be parsed as a date.
    """
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        # dateutil.parser is very flexible — it tries many date formats
        parsed = dateutil_parser.parse(str(value).strip(), dayfirst=True)
        return parsed.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        return None


def parse_amount(value) -> float | None:
    """
    Parse an amount value to a float.

    Handles:
        - Commas in numbers: "1,234.56" → 1234.56
        - Currency symbols: "₹1,234" → 1234.0
        - Parentheses for negative: "(500)" → -500.0
        - Already a float or int

    Returns None if the value cannot be interpreted as a number.
    """
    if pd.isna(value):
        return None

    val = str(value).strip()

    # Empty string
    if not val:
        return None

    # Handle parentheses notation: (500) means -500
    is_negative = val.startswith("(") and val.endswith(")")
    if is_negative:
        val = val[1:-1]

    # Remove currency symbols and commas
    for char in ["₹", "$", "€", "£", "¥", ",", " "]:
        val = val.replace(char, "")

    try:
        result = float(val)
        return -abs(result) if is_negative else result
    except ValueError:
        return None


def determine_sign(amount: float, txn_type: str | None,
                   is_debit_col: bool = False, is_credit_col: bool = False) -> float:
    """
    Apply the correct sign to an amount based on transaction type.

    Rules (in order of priority):
        1. If amount already has a sign AND is from the 'amount' column: use as-is
        2. If from a 'debit' column: always make negative
        3. If from a 'credit' column: always make positive
        4. If txn_type is 'debit'/'dr'/'withdrawal': make negative
        5. If txn_type is 'credit'/'cr'/'deposit': make positive
        6. Default: use the sign of the amount as uploaded
    """
    if is_debit_col:
        return -abs(amount)   # Debits are always expenses (negative)

    if is_credit_col:
        return abs(amount)    # Credits are always income (positive)

    if txn_type:
        txn_type_lower = str(txn_type).lower().strip()
        if txn_type_lower in ("debit", "dr", "withdrawal", "expense"):
            return -abs(amount)
        elif txn_type_lower in ("credit", "cr", "deposit", "income"):
            return abs(amount)

    # If amount already has a sign (user uploaded negative numbers), trust it
    return amount


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Main Validation Function
# ─────────────────────────────────────────────────────────────────────────────

def validate_and_clean(
    df: pd.DataFrame,
    col_map: dict,
    existing_hashes: set = None,
) -> dict:
    """
    Validate every row in the DataFrame. Return a report.

    Returns a dict:
    {
        "valid_rows":    [list of clean dicts ready for DB insert],
        "rejected_rows": [list of {"row": n, "data": {...}, "reason": "..."}],
        "duplicate_rows": [list of dicts],
        "stats": {
            "total": 90,
            "valid": 85,
            "rejected": 3,
            "duplicates": 2
        }
    }
    """
    if existing_hashes is None:
        existing_hashes = set()

    valid_rows = []
    rejected_rows = []
    duplicate_rows = []

    for row_idx, row in df.iterrows():
        row_num = row_idx + 2  # +2: 1 for header, 1 for 1-based counting

        # ── Step 1: Extract date ──────────────────────────────────────────────
        date_col = col_map.get("date")
        raw_date = row[date_col] if date_col else None
        parsed_date = parse_date(raw_date)

        if not parsed_date:
            rejected_rows.append({
                "row": row_num,
                "data": row.to_dict(),
                "reason": f"Invalid or missing date: '{raw_date}'",
            })
            continue

        # ── Step 2: Extract description ───────────────────────────────────────
        desc_col = col_map.get("description")
        description = str(row[desc_col]).strip() if desc_col and not pd.isna(row[desc_col]) else ""

        if not description:
            description = "Unknown Transaction"

        # ── Step 3: Extract amount ────────────────────────────────────────────
        amount_col   = col_map.get("amount")
        debit_col    = col_map.get("debit")
        credit_col   = col_map.get("credit")
        type_col     = col_map.get("type")

        txn_type = str(row[type_col]).strip().lower() if type_col and not pd.isna(row[type_col]) else None
        raw_amount = None
        is_debit = False
        is_credit = False

        if amount_col and not pd.isna(row[amount_col]):
            # Single amount column
            raw_amount = parse_amount(row[amount_col])
        elif debit_col and credit_col:
            # Separate debit / credit columns
            debit_val  = parse_amount(row[debit_col])  if not pd.isna(row.get(debit_col, float("nan"))) else None
            credit_val = parse_amount(row[credit_col]) if not pd.isna(row.get(credit_col, float("nan"))) else None

            if debit_val and debit_val != 0:
                raw_amount = debit_val
                is_debit = True
            elif credit_val and credit_val != 0:
                raw_amount = credit_val
                is_credit = True
        elif debit_col:
            raw_amount = parse_amount(row[debit_col])
            is_debit = True
        elif credit_col:
            raw_amount = parse_amount(row[credit_col])
            is_credit = True

        if raw_amount is None:
            rejected_rows.append({
                "row": row_num,
                "data": row.to_dict(),
                "reason": "Missing or invalid amount",
            })
            continue

        if raw_amount == 0:
            rejected_rows.append({
                "row": row_num,
                "data": row.to_dict(),
                "reason": "Amount is zero — skipped",
            })
            continue

        # Apply sign convention
        final_amount = determine_sign(raw_amount, txn_type, is_debit, is_credit)

        # Derive transaction_type string
        if final_amount > 0:
            final_type = "credit"
        else:
            final_type = "debit"

        # ── Step 4: Extract pre-assigned category (optional) ──────────────────
        cat_col = col_map.get("category")
        pre_category = None
        if cat_col and not pd.isna(row.get(cat_col, float("nan"))):
            pre_category = str(row[cat_col]).strip()
            if pre_category not in CATEGORIES:
                pre_category = None   # Ignore unknown categories

        # Auto-categorize if no valid category was provided
        category_name = pre_category or categorize_transaction(description, final_amount)

        # ── Step 5: Duplicate detection ───────────────────────────────────────
        txn_hash = (parsed_date, description, final_amount)
        if txn_hash in existing_hashes:
            duplicate_rows.append({
                "transaction_date": parsed_date,
                "description":      description,
                "amount":           final_amount,
                "category_name":    category_name,
                "transaction_type": final_type,
            })
            continue

        # Track this hash so we don't add it twice from the same CSV
        existing_hashes.add(txn_hash)

        # ── Step 6: Build clean row ───────────────────────────────────────────
        valid_rows.append({
            "transaction_date": parsed_date,
            "description":      description,
            "amount":           round(final_amount, 2),
            "transaction_type": final_type,
            "category_name":    category_name,
            "notes":            "",
        })

    return {
        "valid_rows":     valid_rows,
        "rejected_rows":  rejected_rows,
        "duplicate_rows": duplicate_rows,
        "stats": {
            "total":      len(df),
            "valid":      len(valid_rows),
            "rejected":   len(rejected_rows),
            "duplicates": len(duplicate_rows),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — File Reading
# ─────────────────────────────────────────────────────────────────────────────

def read_csv_file(file_obj) -> tuple[pd.DataFrame | None, str | None]:
    """
    Read a CSV from a file-like object (Streamlit's UploadedFile).

    Returns:
        (DataFrame, None)        on success
        (None, "error message")  on failure

    Validates:
        - File size ≤ MAX_CSV_SIZE_MB
        - Row count ≤ MAX_CSV_ROWS
        - At least 2 columns
        - At least 1 row of data
    """
    try:
        # Check file size
        content = file_obj.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_CSV_SIZE_MB:
            return None, f"File too large ({size_mb:.1f} MB). Maximum allowed: {MAX_CSV_SIZE_MB} MB."

        # Parse CSV
        df = pd.read_csv(io.BytesIO(content))

        # Basic shape validation
        if len(df) == 0:
            return None, "The CSV file is empty (no data rows found)."

        if len(df.columns) < 2:
            return None, "The CSV must have at least 2 columns (date and amount)."

        if len(df) > MAX_CSV_ROWS:
            return None, (
                f"Too many rows ({len(df):,}). "
                f"Maximum allowed: {MAX_CSV_ROWS:,}. "
                f"Please split the file into smaller batches."
            )

        # Strip whitespace from column names
        df.columns = df.columns.str.strip()

        return df, None

    except pd.errors.EmptyDataError:
        return None, "The file is empty or contains no valid CSV data."
    except pd.errors.ParserError as e:
        return None, f"Could not parse the CSV: {e}"
    except Exception as e:
        return None, f"Unexpected error reading file: {e}"


def process_uploaded_file(file_obj, existing_hashes: set = None) -> dict:
    """
    Full pipeline: read → detect columns → validate → return results.

    This is the function called by the Transactions page upload handler.

    Returns the same dict as validate_and_clean(), plus:
        "col_map": the detected column mapping
        "raw_df":  the original DataFrame (for preview display)
        "error":   error message if reading failed, else None
    """
    if existing_hashes is None:
        existing_hashes = set()

    # Step 1: Read file
    df, error = read_csv_file(file_obj)
    if error:
        return {"error": error, "stats": {"total": 0, "valid": 0, "rejected": 0, "duplicates": 0}}

    # Step 2: Detect columns
    col_map = detect_columns(df)

    # Check for minimum required columns
    if not col_map.get("date"):
        return {
            "error": (
                "Could not find a date column. Expected one of: "
                + ", ".join(CSV_COLUMN_ALIASES["date"])
            ),
            "raw_df": df,
            "col_map": col_map,
            "stats": {"total": len(df), "valid": 0, "rejected": 0, "duplicates": 0},
        }

    has_amount  = bool(col_map.get("amount"))
    has_debit   = bool(col_map.get("debit"))
    has_credit  = bool(col_map.get("credit"))

    if not (has_amount or has_debit or has_credit):
        return {
            "error": (
                "Could not find an amount column. Expected one of: "
                + ", ".join(CSV_COLUMN_ALIASES["amount"])
            ),
            "raw_df": df,
            "col_map": col_map,
            "stats": {"total": len(df), "valid": 0, "rejected": 0, "duplicates": 0},
        }

    # Step 3: Validate and clean
    result = validate_and_clean(df, col_map, existing_hashes)
    result["col_map"] = col_map
    result["raw_df"]  = df
    result["error"]   = None

    return result



