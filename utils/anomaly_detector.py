# ─────────────────────────────────────────────────────────────────────────────
# utils/anomaly_detector.py — Unusual Spending Detection
#
# PURPOSE:
#   Flags transactions that are unusually high compared to typical spending
#   behavior for that specific category.
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
from utils.config import UNUSUAL_SPENDING_MULTIPLIER, MIN_TRANSACTIONS_FOR_ANOMALY

def detect_unusual_spending(df: pd.DataFrame) -> list[dict]:
    """
    Detects unusual single transactions based on category averages.
    """
    if df.empty:
        return []

    # Only look at expenses
    expenses = df[df['amount'] < 0].copy()
    if expenses.empty:
        return []
        
    alerts = []
    
    # Calculate category baselines
    for category, group in expenses.groupby('category_name'):
        if len(group) < MIN_TRANSACTIONS_FOR_ANOMALY:
            continue
            
        avg_amt = abs(group['amount'].mean())
        threshold = avg_amt * UNUSUAL_SPENDING_MULTIPLIER
        
        # Find outliers
        outliers = group[abs(group['amount']) > threshold]
        
        for _, row in outliers.iterrows():
            alerts.append({
                "transaction_date": row['transaction_date'],
                "description": row['description'],
                "amount": abs(row['amount']),
                "category": category,
                "baseline_avg": avg_amt,
                "threshold": threshold,
                "multiplier": round(abs(row['amount']) / avg_amt, 1),
                "reason": f"Spending is {round(abs(row['amount']) / avg_amt, 1)}x higher than category average (₹{avg_amt:,.2f})"
            })
            
    # Sort by date descending
    alerts.sort(key=lambda x: x['transaction_date'], reverse=True)
    return alerts
