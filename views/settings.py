# ─────────────────────────────────────────────────────────────────────────────
# pages/settings.py — Settings & Data Management
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
from datetime import datetime

from utils.config import THEME
from database.connection import test_connection
from database.schema import get_table_stats, initialize_database, drop_all_tables
from database import queries

def render():
    initialize_database()
    st.markdown(f'<h1 style="color:{THEME["primary"]};">⚙️ Settings & Data Management</h1>', unsafe_allow_html=True)

    tab2, tab3 = st.tabs(["📥 Export Reports", "⚠️ Danger Zone"])

    with tab2:
        st.markdown("### Export Data")
        st.write("Download your analytics data as CSV files.")
        
        if queries.has_transactions():
            col_a, col_b = st.columns(2)
            
            with col_a:
                # All transactions
                df_all = queries.get_all_transactions()
                csv_all = df_all.to_csv(index=False).encode('utf-8')
                st.download_button("Download All Transactions", csv_all, "all_transactions.csv", "text/csv")
                
                # Category summary
                df_cat = queries.get_spending_by_category()
                csv_cat = df_cat.to_csv(index=False).encode('utf-8')
                st.download_button("Download Category Summary", csv_cat, "category_summary.csv", "text/csv")
                
            with col_b:
                # Monthly summary
                df_mon = queries.get_monthly_summary()
                csv_mon = df_mon.to_csv(index=False).encode('utf-8')
                st.download_button("Download Monthly Summary", csv_mon, "monthly_summary.csv", "text/csv")
                
                # Top merchants
                df_merch = queries.get_top_merchants(limit=100)
                csv_merch = df_merch.to_csv(index=False).encode('utf-8')
                st.download_button("Download Top Merchants", csv_merch, "top_merchants.csv", "text/csv")
        else:
            st.info("No data available to export.")

    with tab3:
        st.markdown("### Danger Zone")
        st.warning("These actions cannot be undone.")
        
        if st.button("🗑️ Clear All Transactions (Keep Categories & Budgets)"):
            deleted = queries.delete_all_transactions()
            st.success(f"Deleted {deleted} transactions.")
            st.rerun()
            
        st.markdown("---")
        st.write("Wipe entire database (deletes everything including budgets):")
        if st.button("🚨 Drop All Tables", type="primary"):
            drop_all_tables()
            st.success("All tables dropped. They will be recreated on next load.")
            st.rerun()
