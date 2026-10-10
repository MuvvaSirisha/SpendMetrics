# ─────────────────────────────────────────────────────────────────────────────
# pages/transactions.py — Transaction Import & Management Page
#
# PURPOSE:
#   - Load sample data with one click
#   - Upload a bank CSV file
#   - Preview and validate before importing
#   - View, search, filter, edit category, and delete transactions
#
# FLOW:
#   Upload/Load → validate_and_clean() → preview → confirm → insert_transactions()
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
from datetime import datetime

from utils.config import (
    THEME, CATEGORIES, CATEGORY_ICONS,
    format_currency, TRANSACTIONS_PER_PAGE,
)
from utils.ingestion import process_uploaded_file
from utils.categorization import get_category_reason
from database.schema import initialize_database
from database import queries


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _color_amount(val: float) -> str:
    color = THEME["secondary"] if val > 0 else THEME["danger"]
    sign  = "+" if val > 0 else ""
    return f'<span style="color:{color};font-weight:600">{sign}{format_currency(val)}</span>'


def _import_data(result: dict, filename: str, source: str = "csv"):
    """
    Save validated rows to DB and record the import.
    Returns (import_id, message).
    """
    valid_rows = result.get("valid_rows", [])
    stats      = result["stats"]

    if not valid_rows:
        return None, "No valid rows to import."

    # Record the import first so we get an import_id
    import_id = queries.insert_import_record(
        filename   = filename,
        row_count  = stats["total"],
        accepted   = stats["valid"],
        rejected   = stats["rejected"],
        duplicates = stats["duplicates"],
        source     = source,
    )

    # Attach import_id to each row
    for row in valid_rows:
        row["import_id"] = import_id

    inserted = queries.insert_transactions(valid_rows)
    return import_id, f"✅ Successfully imported **{inserted}** transactions."


# ─────────────────────────────────────────────────────────────────────────────
# SECTION A — Import Panel
# ─────────────────────────────────────────────────────────────────────────────

def _render_import_section():
    """Upload CSV, preview, validate, and confirm import."""

    st.markdown(f"### 📥 Import Transactions")

    st.markdown(
        """
        **Expected CSV format:**

        | Column | Example | Notes |
        |--------|---------|-------|
        | `date` | `2024-09-15` | Required |
        | `description` | `Swiggy Food Order` | Required |
        | `amount` | `-450.00` | Required (negative = expense) |
        | `type` | `debit` | Optional |

        _Also accepts:_ `transaction_date`, `narration`, `withdrawal`/`deposit` columns.
        
        💡 **Note:** You can upload multiple files (e.g., different months or different accounts). They will be combined into a single, shared dashboard.
        """
    )

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        key="csv_uploader",
        help="Max 10 MB / 10,000 rows",
    )

    if uploaded_file is not None:
        existing = queries.get_existing_hashes()
        with st.spinner("Validating your file..."):
            result = process_uploaded_file(uploaded_file, existing)
            result["filename"] = uploaded_file.name

        if result.get("error"):
            st.error(f"❌ {result['error']}")
        else:
            _show_import_preview(result, uploaded_file.name, "csv")


def _show_import_preview(result: dict, filename: str, source: str):
    """Show validation summary and a preview before the user confirms import."""

    stats = result["stats"]

    # ── Summary Banner ─────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📄 Total Rows",    stats["total"])
    col2.metric("✅ Valid",          stats["valid"])
    col3.metric("❌ Rejected",       stats["rejected"])
    col4.metric("⚠️ Duplicates",    stats["duplicates"])

    if stats["valid"] == 0:
        if stats["duplicates"] > 0:
            st.warning(f"Found {stats['duplicates']} rows, but all of them are already in your database (duplicates).")
        else:
            st.error("No valid rows found. Please check the file format.")
        return

    # ── Valid Rows Preview ─────────────────────────────────────────────────────
    st.markdown("#### Preview (first 10 valid rows)")
    valid_df = pd.DataFrame(result["valid_rows"][:10])
    if not valid_df.empty:
        preview_df = valid_df[["transaction_date", "description", "amount", "category_name"]].copy()
        preview_df.columns = ["Date", "Description", "Amount (₹)", "Category"]
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

    # ── Rejected Rows ──────────────────────────────────────────────────────────
    if result["rejected_rows"]:
        with st.expander(f"⚠️ {len(result['rejected_rows'])} Rejected Row(s) — click to see why"):
            for r in result["rejected_rows"][:20]:
                st.markdown(f"- **Row {r['row']}**: {r['reason']}")

    # ── Duplicates ─────────────────────────────────────────────────────────────
    if result["duplicate_rows"]:
        with st.expander(f"♻️ {len(result['duplicate_rows'])} Duplicate(s) — already in database"):
            dup_df = pd.DataFrame(result["duplicate_rows"][:10])
            if not dup_df.empty:
                st.dataframe(dup_df, use_container_width=True, hide_index=True)

    # ── Confirm Button ─────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button(
        f"✅ Confirm Import — Add {stats['valid']} Transactions",
        type="primary",
        key=f"confirm_import_{source}",
    ):
        import_id, msg = _import_data(result, filename, source)
        if import_id:
            st.success(msg)
            st.balloons()
            # Clear the uploader state so user can import again
            st.session_state.pop("csv_uploader", None)
            st.rerun()
        else:
            st.error(msg)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION B — View & Manage Transactions
# ─────────────────────────────────────────────────────────────────────────────

def _render_transactions_table():
    """Search, filter, view, edit, and delete transactions."""

    st.markdown("---")
    st.markdown("### 📋 All Transactions")

    # ── Filters ────────────────────────────────────────────────────────────────
    with st.expander("🔍 Search & Filter", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            search = st.text_input(
                "Search description",
                placeholder="e.g. Swiggy, Amazon...",
                key="txn_search",
            )
        with col2:
            cat_filter = st.selectbox(
                "Category",
                options=["All"] + CATEGORIES,
                key="txn_cat_filter",
            )
        with col3:
            type_filter = st.selectbox(
                "Type",
                options=["All", "debit", "credit"],
                key="txn_type_filter",
            )

        col4, col5 = st.columns(2)
        min_str, max_str = queries.get_date_range()
        if min_str and max_str:
            min_d = datetime.strptime(min_str, "%Y-%m-%d").date()
            max_d = datetime.strptime(max_str, "%Y-%m-%d").date()
        else:
            from datetime import date, timedelta
            min_d = date.today() - timedelta(days=90)
            max_d = date.today()

        with col4:
            start_d = st.date_input("From date", value=min_d, key="txn_start_date")
        with col5:
            end_d   = st.date_input("To date",   value=max_d, key="txn_end_date")

    # ── Fetch ──────────────────────────────────────────────────────────────────
    df = queries.get_all_transactions(
        start_date       = start_d.strftime("%Y-%m-%d"),
        end_date         = end_d.strftime("%Y-%m-%d"),
        category         = cat_filter if cat_filter != "All" else None,
        search_text      = search or None,
        transaction_type = type_filter if type_filter != "All" else None,
    )

    if df.empty:
        st.info("No transactions match your filters.")
        return

    # ── Pagination ─────────────────────────────────────────────────────────────
    total_rows = len(df)
    total_pages = max(1, (total_rows - 1) // TRANSACTIONS_PER_PAGE + 1)

    if "txn_page" not in st.session_state:
        st.session_state["txn_page"] = 1
    page = st.session_state["txn_page"]
    page = max(1, min(page, total_pages))

    page_start = (page - 1) * TRANSACTIONS_PER_PAGE
    page_end   = page_start + TRANSACTIONS_PER_PAGE
    page_df    = df.iloc[page_start:page_end].copy()

    # ── Summary row ────────────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)
    col_a.markdown(f"**{total_rows}** transactions found")
    col_b.markdown(
        f"Total expenses: **{format_currency(df[df['amount'] < 0]['amount'].abs().sum())}**"
    )

    # Download button
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    col_c.download_button(
        "⬇️ Download CSV",
        data=csv_bytes,
        file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="dl_txn",
    )

    # ── Transaction Rows ───────────────────────────────────────────────────────
    for _, row in page_df.iterrows():
        txn_id = int(row["id"])
        amount = float(row["amount"])
        is_income = amount > 0

        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 4, 2, 2, 1])

            with c1:
                st.caption(row["transaction_date"])
            with c2:
                st.markdown(f"**{row['description']}**")
                icon = CATEGORY_ICONS.get(row["category_name"], "📦")
                st.caption(f"{icon} {row['category_name']}")
            with c3:
                color = THEME["secondary"] if is_income else THEME["danger"]
                sign  = "+" if is_income else ""
                st.markdown(
                    f'<span style="color:{color};font-weight:700;font-size:15px">'
                    f'{sign}{format_currency(amount)}</span>',
                    unsafe_allow_html=True,
                )
            with c4:
                # Inline category editor
                new_cat = st.selectbox(
                    "Category",
                    options=CATEGORIES,
                    index=CATEGORIES.index(row["category_name"])
                    if row["category_name"] in CATEGORIES else 0,
                    key=f"cat_{txn_id}",
                    label_visibility="collapsed",
                )
                if new_cat != row["category_name"]:
                    if queries.update_transaction_category(txn_id, new_cat):
                        st.success("Updated!", icon="✅")
                        st.rerun()
            with c5:
                # Delete button with confirmation via session state
                del_key = f"del_{txn_id}"
                if st.session_state.get(del_key):
                    if st.button("⚠️ Yes", key=f"confirm_del_{txn_id}"):
                        queries.delete_transaction(txn_id)
                        st.session_state.pop(del_key, None)
                        st.rerun()
                    if st.button("No", key=f"cancel_del_{txn_id}"):
                        st.session_state.pop(del_key, None)
                        st.rerun()
                else:
                    if st.button("🗑️", key=f"del_btn_{txn_id}", help="Delete transaction"):
                        st.session_state[del_key] = True
                        st.rerun()

        st.divider()

    # ── Pagination Controls ────────────────────────────────────────────────────
    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("← Prev", disabled=(page <= 1), key="txn_prev"):
            st.session_state["txn_page"] = page - 1
            st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:center;padding-top:6px;'>Page {page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Next →", disabled=(page >= total_pages), key="txn_next"):
            st.session_state["txn_page"] = page + 1
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render():
    """Render the Transactions page."""

    try:
        initialize_database()
    except Exception as e:
        st.error(f"⚠️ Database error: {e}")
        return

    st.markdown(
        f'<h1 style="color:{THEME["primary"]}; margin-bottom:4px;">💳 Transactions</h1>'
        f'<p style="color:{THEME["muted"]}; margin-top:0;">Import, view, search, and manage your transactions</p>',
        unsafe_allow_html=True,
    )

    _render_import_section()

    if queries.has_transactions():
        _render_transactions_table()
    else:
        st.info("👆 Import transactions above to get started.")
