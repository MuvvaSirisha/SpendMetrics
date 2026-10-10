import pytest
from utils.categorization import categorize_transaction, get_category_reason

def test_categorize_income():
    assert categorize_transaction("Salary Credit", 50000) == "Salary & Income"
    assert categorize_transaction("Freelance Payment", 12000) == "Salary & Income"

def test_categorize_expense():
    assert categorize_transaction("Swiggy Food Order", -450) == "Food & Dining"
    assert categorize_transaction("Amazon Shopping", -1200) == "Shopping"
    assert categorize_transaction("Uber Ride", -200) == "Travel & Transport"

def test_categorize_unknown():
    # Large positive amount without keyword defaults to Salary & Income
    assert categorize_transaction("Unknown Deposit", 15000) == "Salary & Income"
    # Negative amount without keyword defaults to Other
    assert categorize_transaction("Random Store", -50) == "Other"

def test_category_reason():
    reason = get_category_reason("Netflix Subscription", -649)
    assert "Matched keyword" in reason
    assert "netflix" in reason.lower()
