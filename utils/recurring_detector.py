# ─────────────────────────────────────────────────────────────────────────────
# utils/recurring_detector.py — Recurring Payment Detection
#
# PURPOSE:
#   Identifies potential subscriptions and recurring bills by analyzing
#   transaction history for patterns (similar merchant, similar amount,
#   regular intervals).
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
from datetime import datetime
import numpy as np

from utils.config import (
    RECURRING_MIN_OCCURRENCES,
    RECURRING_AMOUNT_TOLERANCE,
    RECURRING_DAY_TOLERANCE
)

def find_recurring_candidates(df: pd.DataFrame) -> list[dict]:
    """
    Analyze transactions to find recurring payment candidates.
    
    Algorithm:
    1. Filter out income and zero amounts.
    2. Group by merchant (description).
    3. For each merchant, find transactions with similar amounts.
    4. Calculate the average interval between these transactions in days.
    5. If interval is consistent (e.g. ~30 days) and count >= min_occurrences, flag it.
    """
    if df.empty:
        return []

    # Only look at expenses
    expenses = df[df['amount'] < 0].copy()
    if expenses.empty:
        return []
    
    # Convert dates to datetime
    expenses['transaction_date'] = pd.to_datetime(expenses['transaction_date'])
    
    candidates = []
    
    # Group by merchant
    for merchant, group in expenses.groupby('description'):
        if len(group) < RECURRING_MIN_OCCURRENCES:
            continue
            
        # Sort by date
        group = group.sort_values('transaction_date')
        
        # We need a simpler grouping. Let's just look at the average amount 
        # and standard deviation of amount.
        avg_amt = group['amount'].mean()
        std_amt = group['amount'].std()
        
        # If amount varies too much, it's not a fixed subscription (might be a variable bill though)
        # We'll allow up to a certain % variance
        if pd.isna(std_amt):
            std_amt = 0
            
        if abs(std_amt / avg_amt) > RECURRING_AMOUNT_TOLERANCE:
            # Let's try to find exact identical amounts within this merchant
            # Group by amount rounded to 2 decimals
            amt_groups = group.groupby(group['amount'].round(2))
            for amt, sub_group in amt_groups:
                if len(sub_group) >= RECURRING_MIN_OCCURRENCES:
                    _check_intervals(merchant, sub_group, candidates)
        else:
            _check_intervals(merchant, group, candidates)
            
    # Sort candidates by estimated frequency
    candidates.sort(key=lambda x: x['frequency'])
    return candidates

def _check_intervals(merchant: str, group: pd.DataFrame, candidates: list):
    """Helper to check if a group of transactions happens at regular intervals."""
    if len(group) < RECURRING_MIN_OCCURRENCES:
        return
        
    dates = group['transaction_date'].tolist()
    diffs = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
    
    if not diffs:
        return
        
    avg_diff = sum(diffs) / len(diffs)
    
    # Determine frequency string based on average interval
    frequency = "Unknown"
    is_recurring = False
    
    # Allow some tolerance for weekends/holidays (RECURRING_DAY_TOLERANCE)
    if abs(avg_diff - 7) <= RECURRING_DAY_TOLERANCE:
        frequency = "Weekly"
        is_recurring = True
    elif abs(avg_diff - 14) <= RECURRING_DAY_TOLERANCE:
        frequency = "Bi-weekly"
        is_recurring = True
    elif abs(avg_diff - 30) <= RECURRING_DAY_TOLERANCE:
        frequency = "Monthly"
        is_recurring = True
    elif abs(avg_diff - 90) <= RECURRING_DAY_TOLERANCE:
        frequency = "Quarterly"
        is_recurring = True
    elif abs(avg_diff - 365) <= RECURRING_DAY_TOLERANCE:
        frequency = "Yearly"
        is_recurring = True
        
    if is_recurring:
        # Check if all intervals are somewhat close to the average
        # (avoid flagging 3 random transactions that happen to average to 30 days)
        for d in diffs:
            if abs(d - avg_diff) > RECURRING_DAY_TOLERANCE * 2:
                is_recurring = False
                break
                
    if is_recurring:
        candidates.append({
            "merchant": merchant,
            "average_amount": abs(group['amount'].mean()),
            "frequency": frequency,
            "occurrences": len(group),
            "last_date": dates[-1].strftime("%Y-%m-%d"),
            "category": group['category_name'].iloc[0]
        })
