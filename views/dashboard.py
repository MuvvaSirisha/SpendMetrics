# ─────────────────────────────────────────────────────────────────────────────
# pages/dashboard.py — Main Dashboard Page
#
# PURPOSE:
#   The first page users see. Shows a high-level financial summary:
#     - Metric cards (total expenses, income, net cash flow, etc.)
#     - Category spending bar chart
#     - Monthly trend line chart
#     - Income vs Expense comparison chart
#     - Recent transactions table
#
# DATA FLOW:
#   database/queries.py → Pandas DataFrame → Plotly chart → Streamlit page
#
# INTERVIEW TIP:
#   "The dashboard fetches aggregated data from SQLite using SQL GROUP BY
#    queries. I don't load all transactions into Python — I let the database
#    do the heavy lifting and only pull summary numbers."
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, date, timedelta

from utils.config import (
    THEME, CHART_COLORS, APP_ICON,
    format_currency, format_percentage, CATEGORY_ICONS,
)
from database.schema import initialize_database
from database import queries


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _metric_delta_color(value: float) -> str:
    """Return 'normal' for positive delta, 'inverse' for negative."""
    return "normal" if value >= 0 else "inverse"


def _render_empty_state():
    """Show a friendly onboarding message when no transactions exist."""
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
            <div style="text-align:center; padding:40px 20px;
                        background:{THEME['card']}; border-radius:12px;
                        border:1px solid #E0E0E0;">
                <div style="font-size:64px; margin-bottom:16px;">📂</div>
                <h2 style="color:{THEME['primary']}; margin-bottom:8px;">
                    No Transactions Yet
                </h2>
                <p style="color:{THEME['muted']}; font-size:15px; margin-bottom:24px;">
                    Import your bank transactions to see your spending analytics here.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="text-align:center; padding-top:10px;">
                <p style="font-size:16px; color:#1B3A6B; font-weight:600;">
                    👈 Click <b>Transactions</b> in the sidebar to upload a CSV file and get started.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )


def _render_metric_cards(summary: dict):
    """Render the five top-level KPI metric cards."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="💸 Total Expenses",
            value=format_currency(summary["total_expenses"]),
            help="Sum of all debit/expense transactions in the selected period",
        )
    with col2:
        st.metric(
            label="💰 Total Income",
            value=format_currency(summary["total_income"]),
            help="Sum of all credit/income transactions in the selected period",
        )
    with col3:
        net = summary["net_cash_flow"]
        st.metric(
            label="📊 Net Cash Flow",
            value=format_currency(net),
            delta=f"{'Surplus' if net >= 0 else 'Deficit'}",
            delta_color=_metric_delta_color(net),
            help="Income minus Expenses. Positive = saving money.",
        )
    with col4:
        st.metric(
            label="🧾 Transactions",
            value=f"{summary['transaction_count']:,}",
            help="Total number of transactions in the selected period",
        )
    with col5:
        st.metric(
            label="📉 Avg. Expense",
            value=format_currency(summary["avg_expense"]),
            help="Average amount per expense transaction",
        )


def _render_category_chart(cat_df: pd.DataFrame):
    """Horizontal bar chart — spending by category."""
    if cat_df.empty:
        st.info("No expense data to show category breakdown.")
        return

    # Add category icons to labels
    cat_df = cat_df.copy()
    cat_df["label"] = cat_df["category_name"].apply(
        lambda c: f"{CATEGORY_ICONS.get(c, '📦')} {c}"
    )

    fig = px.bar(
        cat_df,
        x="total_spent",
        y="label",
        orientation="h",
        title="💳 Spending by Category",
        labels={"total_spent": "Total Spent (₹)", "label": ""},
        color="total_spent",
        color_continuous_scale=[THEME["accent"], THEME["primary"]],
        text=cat_df["total_spent"].apply(lambda v: format_currency(v)),
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Spent: ₹%{x:,.2f}<extra></extra>",
    )
    fig.update_layout(
        height=max(300, len(cat_df) * 40 + 80),
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=80, t=50, b=20),
        font=dict(family="sans-serif", size=13),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_monthly_trend(monthly_df: pd.DataFrame):
    """Line chart showing monthly expenses and income over time."""
    if monthly_df.empty:
        st.info("No data to show monthly trends.")
        return

    fig = go.Figure()

    # Expense line
    fig.add_trace(go.Scatter(
        x=monthly_df["month"],
        y=monthly_df["total_expenses"],
        name="Expenses",
        mode="lines+markers",
        line=dict(color=THEME["danger"], width=2),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Expenses: ₹%{y:,.2f}<extra></extra>",
    ))

    # Income line
    fig.add_trace(go.Scatter(
        x=monthly_df["month"],
        y=monthly_df["total_income"],
        name="Income",
        mode="lines+markers",
        line=dict(color=THEME["secondary"], width=2),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Income: ₹%{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        title="📈 Monthly Income vs Expenses",
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=50, b=20),
        hovermode="x unified",
    )
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    st.plotly_chart(fig, use_container_width=True)


def _render_category_pie(cat_df: pd.DataFrame):
    """Pie chart showing expense distribution by category."""
    if cat_df.empty:
        return

    # Top 8 categories + "Others"
    if len(cat_df) > 8:
        top = cat_df.head(8).copy()
        others_sum = cat_df.iloc[8:]["total_spent"].sum()
        others_row = pd.DataFrame([{
            "category_name": "Others",
            "total_spent": others_sum,
        }])
        cat_df_plot = pd.concat([top, others_row], ignore_index=True)
    else:
        cat_df_plot = cat_df.copy()

    fig = px.pie(
        cat_df_plot,
        names="category_name",
        values="total_spent",
        title="🥧 Expense Distribution",
        color_discrete_sequence=CHART_COLORS,
        hole=0.35,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>₹%{value:,.2f} (%{percent})<extra></extra>",
    )
    fig.update_layout(
        height=350,
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_top_merchants(merchants_df: pd.DataFrame):
    """Table of top merchants by spending."""
    if merchants_df.empty:
        st.info("No merchant data available.")
        return

    st.markdown("#### 🏪 Top Merchants")
    display_df = merchants_df.copy()
    display_df["total_spent"] = display_df["total_spent"].apply(format_currency)
    display_df["avg_amount"]  = display_df["avg_amount"].apply(format_currency)
    display_df.columns = ["Merchant", "Visits", "Total Spent", "Avg Amount"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def _render_recent_transactions(txn_df: pd.DataFrame):
    """Display the 10 most recent transactions."""
    if txn_df.empty:
        st.info("No recent transactions.")
        return

    st.markdown("#### 🕐 Recent Transactions")
    display_df = txn_df[["transaction_date", "description", "amount",
                          "category_name"]].copy()

    # Format amount with color indicator
    display_df["amount_fmt"] = display_df["amount"].apply(
        lambda a: f"+{format_currency(a)}" if a > 0 else format_currency(a)
    )
    display_df = display_df.drop(columns=["amount"])
    display_df.columns = ["Date", "Description", "Category", "Amount"]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date":        st.column_config.TextColumn("Date", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Category":    st.column_config.TextColumn("Category", width="medium"),
            "Amount":      st.column_config.TextColumn("Amount", width="small"),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def render():
    """Render the Dashboard page."""

    # Initialize DB tables on first load
    try:
        initialize_database()
    except Exception as e:
        st.error(f"⚠️ Database initialization failed: {e}")
        return

    # ── Page Header ────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <h1 style="color:{THEME['primary']}; margin-bottom:4px;">
            {APP_ICON} SpendSense Dashboard
        </h1>
        <p style="color:{THEME['muted']}; font-size:15px; margin-top:0;">
            Your personal finance overview
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ── Check if any data exists ───────────────────────────────────────────────
    if not queries.has_transactions():
        _render_empty_state()
        return

    # ── Date Range Filter ──────────────────────────────────────────────────────
    min_date_str, max_date_str = queries.get_date_range()

    with st.expander("📅 Date Range Filter", expanded=False):
        min_date = datetime.strptime(min_date_str, "%Y-%m-%d").date() if min_date_str else date.today() - timedelta(days=90)
        max_date = datetime.strptime(max_date_str, "%Y-%m-%d").date() if max_date_str else date.today()

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            start_date = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date, key="dash_start")
        with col2:
            end_date = st.date_input("To",   value=max_date, min_value=min_date, max_value=max_date, key="dash_end")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Reset", key="dash_reset"):
                start_date = min_date
                end_date   = max_date

    start_str = start_date.strftime("%Y-%m-%d")
    end_str   = end_date.strftime("%Y-%m-%d")

    if start_date > end_date:
        st.warning("⚠️ Start date is after end date. Please adjust the filter.")
        return

    # ── Fetch Data ─────────────────────────────────────────────────────────────
    summary      = queries.get_dashboard_summary(start_str, end_str)
    cat_df       = queries.get_spending_by_category(start_str, end_str)
    monthly_df   = queries.get_monthly_summary(start_str, end_str)
    recent_df    = queries.get_all_transactions(start_str, end_str, limit=8)

    # ── Metric Cards ───────────────────────────────────────────────────────────
    st.markdown("---")
    _render_metric_cards(summary)

    # ── Top Category Banner ────────────────────────────────────────────────────
    if summary["top_category"] != "—":
        icon = CATEGORY_ICONS.get(summary["top_category"], "📦")
        st.markdown(
            f"""
            <div style="background:{THEME['primary']}; color:white;
                        padding:10px 20px; border-radius:8px; margin:16px 0;
                        font-size:14px;">
                🏆 <b>Highest spending category this period:</b>
                {icon} {summary['top_category']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Main Charts ────────────────────────────────────────────────────────────
    st.markdown("---")
    _render_monthly_trend(monthly_df)

    st.markdown("---")
    col_left, col_right = st.columns([1, 1])
    with col_left:
        _render_category_pie(cat_df)
    with col_right:
        _render_recent_transactions(recent_df)

    # ── Footer note ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        f"📅 Showing data from **{start_str}** to **{end_str}** · "
        f"**{summary['transaction_count']}** transactions · "
        f"Last updated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )

