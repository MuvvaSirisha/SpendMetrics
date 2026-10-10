# ─────────────────────────────────────────────────────────────────────────────
# pages/budgets.py — Budget Tracking Page
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
from datetime import date

from utils.config import THEME, CATEGORIES, format_currency
from database import queries
from database.schema import initialize_database

def render():
    try:
        initialize_database()
    except Exception as e:
        st.error(f"⚠️ Database error: {e}")
        return

    st.markdown(f'<h1 style="color:{THEME["primary"]};">🎯 Insights & Budgets</h1>', unsafe_allow_html=True)
    
    tab_budg, tab_sub, tab_alert = st.tabs(["🎯 Budgets", "🔁 Subscriptions", "⚠️ Unusual Spending"])

    with tab_budg:
        # Select Month
        today = date.today()
        
        col_m, _ = st.columns([1, 3])
        with col_m:
            # Simple string for month 'YYYY-MM'
            month_str = st.text_input("Month (YYYY-MM)", value=today.strftime("%Y-%m"), key="budget_month")
            
        if not month_str or len(month_str) != 7:
            st.error("Please enter a valid month format (YYYY-MM).")
            return

        st.markdown("---")
        
        # Fetch current budgets
        budgets_df = queries.get_budgets(month_year=month_str)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### Budget Progress for {month_str}")
            if budgets_df.empty:
                st.info("No budgets set for this month. Add one on the right!")
            else:
                for _, row in budgets_df.iterrows():
                    cat = row['category_name']
                    budget = row['budget_amount']
                    spent = row['spent']
                    
                    pct = min(1.0, spent / budget) if budget > 0 else 1.0
                    
                    # Determine color based on usage
                    if pct > 0.9:
                        color = "red"
                    elif pct > 0.75:
                        color = "orange"
                    else:
                        color = "green"
                        
                    st.markdown(f"**{cat}** — Spent {format_currency(spent)} of {format_currency(budget)}")
                    st.progress(pct, text=f"{pct*100:.1f}% used")
                    st.markdown("<br>", unsafe_allow_html=True)

        with col2:
            st.markdown("### Set a Budget")
            with st.form("set_budget_form"):
                new_cat = st.selectbox("Category", options=CATEGORIES)
                new_amt = st.number_input("Budget Amount (₹)", min_value=1.0, step=100.0, value=5000.0)
                
                if st.form_submit_button("Save Budget", type="primary"):
                    if queries.upsert_budget(new_cat, month_str, new_amt):
                        st.success(f"Budget for {new_cat} saved!")
                        st.rerun()
                        
            if not budgets_df.empty:
                st.markdown("### Remove a Budget")
                with st.form("remove_budget_form"):
                    del_cat = st.selectbox("Category to remove", options=budgets_df['category_name'].tolist())
                    if st.form_submit_button("Delete Budget"):
                        if queries.delete_budget(del_cat, month_str):
                            st.success(f"Budget for {del_cat} deleted!")
                            st.rerun()

    with tab_sub:
        from utils.recurring_detector import find_recurring_candidates
        df = queries.get_all_transactions()
        
        st.markdown("### Recurring Payment Candidates")
        st.write("We analyzed your transactions to find similar, repeating payments.")
        
        candidates = find_recurring_candidates(df)
        if not candidates:
            st.success("No recurring payments detected.")
        else:
            cand_df = pd.DataFrame(candidates)
            cand_df['average_amount'] = cand_df['average_amount'].apply(format_currency)
            cand_df.columns = ["Merchant", "Est. Amount", "Frequency", "Occurrences", "Last Seen", "Category"]
            st.dataframe(cand_df, use_container_width=True, hide_index=True)

    with tab_alert:
        from utils.anomaly_detector import detect_unusual_spending
        df = queries.get_all_transactions()
        
        st.markdown("### Unusual Spending Alerts")
        st.write("Transactions that are significantly higher than your average spending for that category.")
        
        alerts = detect_unusual_spending(df)
        if not alerts:
            st.success("No unusual spending detected! Great job staying consistent.")
        else:
            for alert in alerts:
                st.warning(
                    f"**{alert['transaction_date']} - {alert['description']}**\n\n"
                    f"Amount: {format_currency(alert['amount'])} ({alert['category']})\n\n"
                    f"*{alert['reason']}*"
                )
