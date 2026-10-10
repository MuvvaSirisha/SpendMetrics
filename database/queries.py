# ─────────────────────────────────────────────────────────────────────────────
# database/queries.py — All SQL Queries as Python Functions
#
# PURPOSE:
#   Every database read and write operation goes through this file.
#   This separates "what to show" (pages/) from "how to fetch it" (here).
#
# PARAMETERIZED QUERIES — Security:
#   We ALWAYS use ? placeholders instead of string formatting:
#       GOOD: cursor.execute("SELECT * FROM t WHERE id = ?", (user_id,))
#       BAD:  cursor.execute(f"SELECT * FROM t WHERE id = {user_id}")
#
#   The bad version allows SQL injection — a user could type malicious SQL
#   into a form field and delete your entire database. Placeholders prevent
#   this by treating all user input as plain data, never as SQL code.
#
# INTERVIEW TIP:
#   "All queries are centralized in queries.py so they're easy to find,
#    test, and optimize. I used parameterized queries throughout to prevent
#    SQL injection attacks."
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
from database.connection import get_connection


# ═══════════════════════════════════════════════════════════════════════════════
# WRITE OPERATIONS (INSERT, UPDATE, DELETE)
# ═══════════════════════════════════════════════════════════════════════════════

def insert_transactions(transactions: list[dict]) -> int:
    """
    Insert a list of transaction dictionaries into the database.

    Each dict must have:
        transaction_date, description, amount, transaction_type,
        category_name, notes, import_id

    Returns:
        Number of rows successfully inserted.

    SQL CONCEPT — INSERT:
        INSERT INTO table (col1, col2) VALUES (?, ?)
        The ? marks are filled in safely by the database driver.
    """
    if not transactions:
        return 0

    conn = get_connection()
    inserted = 0
    try:
        cursor = conn.cursor()
        for txn in transactions:
            cursor.execute(
                """
                INSERT INTO transactions
                    (transaction_date, description, amount, transaction_type,
                     category_name, notes, import_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    txn["transaction_date"],
                    txn["description"],
                    txn["amount"],
                    txn.get("transaction_type", "debit"),
                    txn.get("category_name", "Other"),
                    txn.get("notes", ""),
                    txn.get("import_id"),
                ),
            )
            inserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return inserted


def insert_import_record(filename: str, row_count: int, accepted: int,
                          rejected: int, duplicates: int, source: str = "csv") -> int:
    """
    Record a CSV import in the import_history table.
    Returns the new import record's ID (used as import_id in transactions).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO import_history
                (filename, row_count, accepted_count, rejected_count,
                 duplicate_count, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (filename, row_count, accepted, rejected, duplicates, source),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_transaction_category(transaction_id: int, category_name: str,
                                 notes: str = "") -> bool:
    """
    Update a transaction's category and optional notes.

    SQL CONCEPT — UPDATE with WHERE:
        We must specify WHERE id = ? to update only ONE row.
        Without WHERE, UPDATE changes EVERY row — a common beginner mistake!
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE transactions
            SET category_name = ?,
                notes         = ?,
                updated_at    = datetime('now')
            WHERE id = ?
            """,
            (category_name, notes, transaction_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_transaction(transaction_id: int) -> bool:
    """
    Delete a single transaction by its ID.

    SQL CONCEPT — DELETE with WHERE:
        Same warning as UPDATE — always use WHERE!
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM transactions WHERE id = ?",
            (transaction_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_all_transactions() -> int:
    """Delete every transaction. Used in Settings → Clear Data."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM import_history")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def upsert_budget(category_name: str, month_year: str, amount: float) -> bool:
    """
    Insert or update a budget for (category, month).

    INSERT OR REPLACE:
        If a budget for this (category, month) already exists, replace it.
        If it doesn't exist, insert it.
        This is SQLite's way of doing "upsert" (update + insert).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO budgets
                (category_name, month_year, amount, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (category_name, month_year, amount),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_budget(category_name: str, month_year: str) -> bool:
    """Delete a budget for a specific category and month."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM budgets WHERE category_name = ? AND month_year = ?",
            (category_name, month_year),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# READ OPERATIONS (SELECT)
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_transactions(
    start_date: str = None,
    end_date: str = None,
    category: str = None,
    search_text: str = None,
    transaction_type: str = None,
    limit: int = None,
) -> pd.DataFrame:
    """
    Fetch transactions with optional filters. Returns a Pandas DataFrame.

    SQL CONCEPTS USED:
        WHERE  — filters rows
        AND    — combines multiple conditions
        LIKE   — partial text match (% is a wildcard)
        ORDER BY — sorts results
        LIMIT  — restricts number of rows returned

    Why return a DataFrame instead of a list?
        Pandas DataFrames are much easier to display in Streamlit (st.dataframe),
        filter, sort, and pass to Plotly for charts.
    """
    conn = get_connection()
    try:
        # Build the WHERE clause dynamically based on which filters are provided
        conditions = ["1=1"]   # "1=1" always matches — a safe starting condition
        params = []

        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)

        if category and category != "All":
            conditions.append("category_name = ?")
            params.append(category)

        if search_text:
            # LIKE '%keyword%' = "description contains keyword"
            conditions.append("LOWER(description) LIKE LOWER(?)")
            params.append(f"%{search_text}%")

        if transaction_type and transaction_type != "All":
            conditions.append("transaction_type = ?")
            params.append(transaction_type)

        where_clause = " AND ".join(conditions)
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT
                id,
                transaction_date,
                description,
                amount,
                transaction_type,
                category_name,
                notes,
                created_at
            FROM transactions
            WHERE {where_clause}
            ORDER BY transaction_date DESC, id DESC
            {limit_clause}
        """

        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()


def get_spending_by_category(
    start_date: str = None,
    end_date: str = None,
) -> pd.DataFrame:
    """
    Total spending grouped by category, excluding income.

    SQL CONCEPTS USED:
        GROUP BY  — groups rows with the same category_name together
        SUM()     — adds up the amounts in each group
        ABS()     — absolute value (turns -450 into 450 for display)
        WHERE amount < 0  — only include expenses (negative amounts)
        ORDER BY total_spent DESC  — highest spending first

    INTERVIEW EXPLANATION:
        "GROUP BY is like sorting cards into piles by suit, then counting
         each pile. Here we sort transactions into category piles,
         then sum the amounts in each pile."
    """
    conn = get_connection()
    try:
        conditions = ["amount < 0"]  # Only expenses
        params = []

        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                category_name,
                COUNT(*)          AS transaction_count,
                ABS(SUM(amount))  AS total_spent,
                ABS(AVG(amount))  AS avg_transaction
            FROM transactions
            WHERE {where_clause}
            GROUP BY category_name
            ORDER BY total_spent DESC
        """

        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def get_monthly_summary(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Monthly spending and income summary.

    SQL CONCEPTS USED:
        strftime('%Y-%m', transaction_date) — extracts 'YYYY-MM' from a date
            e.g. '2024-09-15' → '2024-09'
        CASE WHEN — conditional expression (like if/else inside SQL)
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END)
            = "sum only the negative amounts (expenses)"

    INTERVIEW EXPLANATION:
        "strftime is SQLite's date formatting function. I use it to group
         all transactions in the same month together, regardless of the day."
    """
    conn = get_connection()
    try:
        conditions = ["1=1"]
        params = []

        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                strftime('%Y-%m', transaction_date)  AS month,
                COUNT(*)                              AS transaction_count,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END)
                                                      AS total_expenses,
                SUM(CASE WHEN amount > 0 THEN amount  ELSE 0 END)
                                                      AS total_income,
                SUM(amount)                           AS net_cash_flow
            FROM transactions
            WHERE {where_clause}
            GROUP BY month
            ORDER BY month ASC
        """

        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def get_dashboard_summary(start_date: str = None, end_date: str = None) -> dict:
    """
    Compute all the top-level metric card values for the dashboard.

    Returns a dict with keys:
        total_expenses, total_income, net_cash_flow,
        transaction_count, avg_transaction, top_category

    SQL CONCEPTS USED:
        Aggregate functions: SUM(), COUNT(), AVG()
        Subquery: a SELECT inside another SELECT to get top_category

    INTERVIEW EXPLANATION:
        "I compute summary stats in one SQL query instead of fetching all
         rows and summing in Python, because SQL aggregations run much
         faster in the database engine, especially with large datasets."
    """
    conn = get_connection()
    try:
        conditions = ["1=1"]
        params = []

        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)

        where_clause = " AND ".join(conditions)

        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT
                COUNT(*)                                        AS transaction_count,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END)
                                                                AS total_expenses,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)
                                                                AS total_income,
                SUM(amount)                                     AS net_cash_flow,
                AVG(CASE WHEN amount < 0 THEN ABS(amount) END)  AS avg_expense
            FROM transactions
            WHERE {where_clause}
            """,
            params,
        )
        row = cursor.fetchone()

        # Subquery: which category has the most total spending?
        cursor.execute(
            f"""
            SELECT category_name
            FROM transactions
            WHERE amount < 0 AND {where_clause}
            GROUP BY category_name
            ORDER BY SUM(ABS(amount)) DESC
            LIMIT 1
            """,
            params,
        )
        top_cat_row = cursor.fetchone()

        return {
            "transaction_count": int(row[0] or 0),
            "total_expenses":    float(row[1] or 0),
            "total_income":      float(row[2] or 0),
            "net_cash_flow":     float(row[3] or 0),
            "avg_expense":       float(row[4] or 0),
            "top_category":      top_cat_row[0] if top_cat_row else "—",
        }
    finally:
        conn.close()


def get_top_merchants(
    start_date: str = None,
    end_date: str = None,
    limit: int = 10,
) -> pd.DataFrame:
    """
    Top merchants by total spending.

    SQL CONCEPTS USED:
        LIMIT — return only top N results
        ORDER BY ... DESC — highest first
    """
    conn = get_connection()
    try:
        conditions = ["amount < 0"]
        params = []

        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                description                 AS merchant,
                COUNT(*)                    AS visit_count,
                ABS(SUM(amount))            AS total_spent,
                ABS(AVG(amount))            AS avg_amount
            FROM transactions
            WHERE {where_clause}
            GROUP BY description
            ORDER BY total_spent DESC
            LIMIT ?
        """

        return pd.read_sql_query(query, conn, params=params + [limit])
    finally:
        conn.close()


def get_daily_spending(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Daily spending totals — used for the trend line chart."""
    conn = get_connection()
    try:
        conditions = ["amount < 0"]
        params = []

        if start_date:
            conditions.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("transaction_date <= ?")
            params.append(end_date)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                transaction_date            AS date,
                ABS(SUM(amount))            AS daily_spending,
                COUNT(*)                    AS transaction_count
            FROM transactions
            WHERE {where_clause}
            GROUP BY transaction_date
            ORDER BY transaction_date ASC
        """

        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def get_budgets(month_year: str = None) -> pd.DataFrame:
    """
    Fetch budgets with actual spending for the given month.

    SQL CONCEPTS USED:
        LEFT JOIN — keeps all budget rows even if no transactions exist
                    for that category yet.
        Subquery  — calculates spending per category for the specific month.

    INTERVIEW EXPLANATION:
        "I used a LEFT JOIN so categories with a budget but zero spending
         still appear in the results with spent=0. An INNER JOIN would
         silently drop them."
    """
    conn = get_connection()
    try:
        params = []
        month_filter = ""
        spending_month_filter = ""

        if month_year:
            month_filter = "WHERE b.month_year = ?"
            params.append(month_year)
            spending_month_filter = "AND strftime('%Y-%m', transaction_date) = ?"
            params.append(month_year)

        query = f"""
            SELECT
                b.category_name,
                b.month_year,
                b.amount          AS budget_amount,
                COALESCE(
                    (SELECT ABS(SUM(t.amount))
                     FROM transactions t
                     WHERE t.category_name = b.category_name
                       AND t.amount < 0
                       {spending_month_filter}
                    ), 0
                )                 AS spent,
                b.updated_at
            FROM budgets b
            {month_filter}
            ORDER BY b.category_name
        """

        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def has_transactions() -> bool:
    """Return True if at least one transaction exists in the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions")
        return cursor.fetchone()[0] > 0
    finally:
        conn.close()


def get_date_range() -> tuple[str, str]:
    """
    Return the earliest and latest transaction dates.
    Returns ('', '') if there are no transactions.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MIN(transaction_date), MAX(transaction_date)
            FROM transactions
        """)
        row = cursor.fetchone()
        return (row[0] or "", row[1] or "")
    finally:
        conn.close()


def get_existing_hashes() -> set:
    """
    Return a set of (date, description, amount) tuples for duplicate detection.
    Used during CSV import to skip transactions already in the database.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_date, description, amount
            FROM transactions
        """)
        return {(row[0], row[1], row[2]) for row in cursor.fetchall()}
    finally:
        conn.close()


def get_import_history() -> pd.DataFrame:
    """Fetch all import records ordered by most recent first."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                id, filename, imported_at, row_count,
                accepted_count, rejected_count, duplicate_count, source
            FROM import_history
            ORDER BY imported_at DESC
            """,
            conn,
        )
    finally:
        conn.close()


def get_month_over_month_comparison() -> pd.DataFrame:
    """
    Compare spending between the current month and previous month.

    SQL CONCEPT — CTE (Common Table Expression):
        A CTE is a named temporary result set. We define it with WITH,
        then use it like a regular table in the main query.

        WHY USE CTE?
        Instead of writing the same subquery twice, we write it once
        as a CTE and reference it by name. This makes complex SQL
        much easier to read and maintain.

    INTERVIEW EXPLANATION:
        "I used a CTE to calculate monthly totals first, then joined
         the CTE with itself (self-join) to put the current month
         and previous month on the same row for comparison."
    """
    conn = get_connection()
    try:
        query = """
            WITH monthly_totals AS (
                -- Step 1: Calculate total expenses per month
                SELECT
                    strftime('%Y-%m', transaction_date) AS month,
                    ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) AS total_expenses
                FROM transactions
                GROUP BY month
            )
            -- Step 2: Compare each month to the previous month using LAG
            -- (LAG is a window function — it looks at the previous row)
            SELECT
                month,
                total_expenses,
                LAG(total_expenses) OVER (ORDER BY month) AS prev_month_expenses,
                total_expenses - LAG(total_expenses) OVER (ORDER BY month)
                    AS month_change
            FROM monthly_totals
            ORDER BY month DESC
            LIMIT 6
        """
        return pd.read_sql_query(query, conn)
    except Exception:
        # LAG() requires SQLite 3.25+ (2018). Fall back to basic query.
        query = """
            SELECT
                strftime('%Y-%m', transaction_date) AS month,
                ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) AS total_expenses,
                COUNT(*) AS transaction_count
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
            LIMIT 6
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()
