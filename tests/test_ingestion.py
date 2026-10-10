import pytest
import pandas as pd
from utils.ingestion import determine_sign, parse_amount, parse_date

def test_parse_amount():
    assert parse_amount("1,234.56") == 1234.56
    assert parse_amount("₹500") == 500.0
    assert parse_amount("(150)") == -150.0
    assert parse_amount("-200.5") == -200.5

def test_determine_sign():
    # Already signed
    assert determine_sign(-450, None) == -450
    assert determine_sign(1200, None) == 1200
    
    # Based on debit/credit columns
    assert determine_sign(500, None, is_debit_col=True) == -500
    assert determine_sign(500, None, is_credit_col=True) == 500
    
    # Based on type string
    assert determine_sign(500, "debit") == -500
    assert determine_sign(500, "credit") == 500

def test_parse_date():
    assert parse_date("2024-09-15") == "2024-09-15"
    assert parse_date("15/09/2024") == "2024-09-15"
    assert parse_date("invalid") is None
