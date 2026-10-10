# ─────────────────────────────────────────────────────────────────────────────
# utils/categorization.py — Rule-Based Transaction Categorization
#
# PURPOSE:
#   Automatically assigns a category to a transaction based on keywords
#   found in the merchant description.
#
# HOW IT WORKS:
#   1. We define a list of (keyword, category) rules.
#   2. For each transaction, we check if the description contains any keyword.
#   3. The FIRST matching rule wins (order matters!).
#   4. If no rule matches, we assign "Other".
#
# WHY RULE-BASED (not machine learning)?
#   - Completely transparent — you can read exactly why a transaction was categorized
#   - Easy to modify — add a new keyword in 10 seconds
#   - No training data needed
#   - Explainable in interviews: "I can show you exactly which rule fired"
#
# ADDING NEW RULES:
#   Add a tuple to CATEGORIZATION_RULES: ("keyword", "Category Name")
#   Keywords are case-insensitive. Put more specific rules BEFORE general ones.
#
# INTERVIEW TIP:
#   "The categorization is keyword-based. Each rule is (keyword, category).
#    I check the description against every rule in order and assign the
#    first match. This is O(n*m) where n=rules and m=transactions, which
#    is fine for personal finance volumes."
# ─────────────────────────────────────────────────────────────────────────────

from utils.config import CATEGORIES

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIZATION RULES
# Format: (keyword_in_description, category_name)
# Keywords are matched case-insensitively using 'keyword in description.lower()'
#
# ORDER MATTERS:
#   More specific patterns come BEFORE general ones.
#   "salary" before "transfer" — so salary credits aren't labelled as transfers.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIZATION_RULES: list[tuple[str, str]] = [

    # ── Salary & Income ────────────────────────────────────────────────────────
    ("salary",              "Salary & Income"),
    ("payroll",             "Salary & Income"),
    ("freelance",           "Salary & Income"),
    ("stipend",             "Salary & Income"),
    ("consulting fee",      "Salary & Income"),
    ("honorarium",          "Salary & Income"),
    ("dividend",            "Salary & Income"),
    ("interest credit",     "Salary & Income"),
    ("opening balance",     "Salary & Income"),

    # ── Rent & Housing ─────────────────────────────────────────────────────────
    ("house rent",          "Rent"),
    ("rental",              "Rent"),
    ("pg rent",             "Rent"),
    ("accommodation",       "Rent"),
    ("hostel fee",          "Rent"),

    # ── Groceries ──────────────────────────────────────────────────────────────
    ("dmart",               "Groceries"),
    ("d-mart",              "Groceries"),
    ("big bazaar",          "Groceries"),
    ("reliance fresh",      "Groceries"),
    ("more supermarket",    "Groceries"),
    ("nature's basket",     "Groceries"),
    ("licious",             "Groceries"),
    ("grofers",             "Groceries"),
    ("blinkit",             "Groceries"),
    ("zepto",               "Groceries"),
    ("grocery",             "Groceries"),
    ("supermarket",         "Groceries"),
    ("kirana",              "Groceries"),
    ("vegetables",          "Groceries"),
    ("fruits",              "Groceries"),

    # ── Food & Dining ──────────────────────────────────────────────────────────
    ("swiggy",              "Food & Dining"),
    ("zomato",              "Food & Dining"),
    ("dominos",             "Food & Dining"),
    ("pizza hut",           "Food & Dining"),
    ("mcdonald",            "Food & Dining"),
    ("kfc",                 "Food & Dining"),
    ("subway",              "Food & Dining"),
    ("burger king",         "Food & Dining"),
    ("haldirams",           "Food & Dining"),
    ("barbeque nation",     "Food & Dining"),
    ("restaurant",          "Food & Dining"),
    ("cafe",                "Food & Dining"),
    ("coffee",              "Food & Dining"),
    ("food order",          "Food & Dining"),
    ("food delivery",       "Food & Dining"),
    ("dining",              "Food & Dining"),
    ("biryani",             "Food & Dining"),
    ("chai",                "Food & Dining"),
    ("canteen",             "Food & Dining"),

    # ── Travel & Transport ─────────────────────────────────────────────────────
    ("uber",                "Travel & Transport"),
    ("ola",                 "Travel & Transport"),
    ("rapido",              "Travel & Transport"),
    ("indigo",              "Travel & Transport"),
    ("air india",           "Travel & Transport"),
    ("spicejet",            "Travel & Transport"),
    ("goibibo",             "Travel & Transport"),
    ("makemytrip",          "Travel & Transport"),
    ("irctc",               "Travel & Transport"),
    ("railway",             "Travel & Transport"),
    ("metro",               "Travel & Transport"),
    ("bmtc",                "Travel & Transport"),
    ("bus pass",            "Travel & Transport"),
    ("cab",                 "Travel & Transport"),
    ("taxi",                "Travel & Transport"),
    ("auto",                "Travel & Transport"),
    ("petrol",              "Travel & Transport"),
    ("fuel",                "Travel & Transport"),
    ("toll",                "Travel & Transport"),
    ("flight",              "Travel & Transport"),
    ("airways",             "Travel & Transport"),
    ("airport",             "Travel & Transport"),

    # ── Bills & Utilities ──────────────────────────────────────────────────────
    ("electricity",         "Bills & Utilities"),
    ("bescom",              "Bills & Utilities"),
    ("water bill",          "Bills & Utilities"),
    ("bwssb",               "Bills & Utilities"),
    ("gas bill",            "Bills & Utilities"),
    ("broadband",           "Bills & Utilities"),
    ("bsnl",                "Bills & Utilities"),
    ("airtel",              "Bills & Utilities"),
    ("jio recharge",        "Bills & Utilities"),
    ("vi recharge",         "Bills & Utilities"),
    ("mobile recharge",     "Bills & Utilities"),
    ("internet bill",       "Bills & Utilities"),
    ("postpaid",            "Bills & Utilities"),
    ("utility",             "Bills & Utilities"),
    ("municipal",           "Bills & Utilities"),
    ("emi",                 "Bills & Utilities"),

    # ── Subscriptions ──────────────────────────────────────────────────────────
    ("netflix",             "Subscriptions"),
    ("spotify",             "Subscriptions"),
    ("amazon prime",        "Subscriptions"),
    ("hotstar",             "Subscriptions"),
    ("zee5",                "Subscriptions"),
    ("sonyliv",             "Subscriptions"),
    ("youtube premium",     "Subscriptions"),
    ("apple music",         "Subscriptions"),
    ("subscription",        "Subscriptions"),
    ("monthly plan",        "Subscriptions"),

    # ── Education ──────────────────────────────────────────────────────────────
    ("coursera",            "Education"),
    ("udemy",               "Education"),
    ("unacademy",           "Education"),
    ("byju",                "Education"),
    ("vedantu",             "Education"),
    ("school fee",          "Education"),
    ("college fee",         "Education"),
    ("tuition",             "Education"),
    ("exam fee",            "Education"),
    ("book bazaar",         "Education"),
    ("university",          "Education"),
    ("course",              "Education"),
    ("library",             "Education"),

    # ── Healthcare ─────────────────────────────────────────────────────────────
    ("apollo pharmacy",     "Healthcare"),
    ("medplus",             "Healthcare"),
    ("1mg",                 "Healthcare"),
    ("netmeds",             "Healthcare"),
    ("hospital",            "Healthcare"),
    ("clinic",              "Healthcare"),
    ("doctor",              "Healthcare"),
    ("pharmacy",            "Healthcare"),
    ("medicine",            "Healthcare"),
    ("diagnostic",          "Healthcare"),
    ("lab test",            "Healthcare"),
    ("health insurance",    "Healthcare"),
    ("dental",              "Healthcare"),
    ("optician",            "Healthcare"),
    ("chemist",             "Healthcare"),

    # ── Entertainment ──────────────────────────────────────────────────────────
    ("pvr",                 "Entertainment"),
    ("inox",                "Entertainment"),
    ("cinema",              "Entertainment"),
    ("movie",               "Entertainment"),
    ("bookmyshow",          "Entertainment"),
    ("gaming",              "Entertainment"),
    ("steam",               "Entertainment"),
    ("playstation",         "Entertainment"),
    ("concert",             "Entertainment"),
    ("event ticket",        "Entertainment"),
    ("amusement",           "Entertainment"),
    ("zoo",                 "Entertainment"),
    ("museum",              "Entertainment"),

    # ── Shopping ───────────────────────────────────────────────────────────────
    ("amazon",              "Shopping"),
    ("flipkart",            "Shopping"),
    ("myntra",              "Shopping"),
    ("ajio",                "Shopping"),
    ("meesho",              "Shopping"),
    ("nykaa",               "Shopping"),
    ("snapdeal",            "Shopping"),
    ("lifestyle",           "Shopping"),
    ("shoppers stop",       "Shopping"),
    ("h&m",                 "Shopping"),
    ("zara",                "Shopping"),
    ("shopping",            "Shopping"),
    ("purchase",            "Shopping"),

    # ── Transfers ──────────────────────────────────────────────────────────────
    ("upi transfer",        "Transfers"),
    ("neft",                "Transfers"),
    ("rtgs",                "Transfers"),
    ("imps",                "Transfers"),
    ("credit card payment", "Transfers"),
    ("card payment",        "Transfers"),
    ("transfer to",         "Transfers"),
    ("transfer from",       "Transfers"),
    ("self transfer",       "Transfers"),
    ("account transfer",    "Transfers"),
    ("wallet",              "Transfers"),
    ("paytm",               "Transfers"),
    ("phonepe",             "Transfers"),
    ("gpay",                "Transfers"),
    ("google pay",          "Transfers"),

]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CATEGORIZATION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def categorize_transaction(description: str, amount: float = None) -> str:
    """
    Assign a category to a transaction based on its description.

    Args:
        description: The merchant name / transaction narration
        amount:      The signed amount (positive = income, negative = expense).
                     Used to auto-assign "Salary & Income" for large credits.

    Returns:
        A category name from utils.config.CATEGORIES

    Algorithm:
        1. If amount is positive and large (>= 10000), likely income
        2. Check description against each keyword rule in order
        3. Return first match, or "Other" if nothing matched

    Example:
        categorize_transaction("Swiggy Food Order", -450)
        → "Food & Dining"  (matched keyword "swiggy")

        categorize_transaction("SALARY JUNE 2024", 65000)
        → "Salary & Income"  (matched keyword "salary")
    """
    # Edge case: empty description
    if not description:
        return _income_or_other(amount)

    description_lower = description.lower().strip()

    # Rule 1: Large positive amount with no other match likely means income
    # (We check this first so "Salary Credit" doesn't accidentally match "credit card")
    if amount is not None and amount > 0 and amount >= 10000:
        # Still check rules in case description says "salary" etc.
        pass

    # Rule 2: Check keyword rules in order
    for keyword, category in CATEGORIZATION_RULES:
        if keyword.lower() in description_lower:
            return category

    # Rule 3: No keyword matched — use amount sign as a last resort
    return _income_or_other(amount)


def _income_or_other(amount: float | None) -> str:
    """Return 'Salary & Income' for positive amounts, 'Other' otherwise."""
    if amount is not None and amount > 0:
        return "Salary & Income"
    return "Other"


def get_category_reason(description: str, amount: float = None) -> str:
    """
    Return a human-readable explanation of why a transaction was categorized.

    Used in the Transactions page to show users the reasoning.

    Example:
        get_category_reason("Swiggy Food Order", -450)
        → 'Matched keyword "swiggy" → Food & Dining'
    """
    if not description:
        return "Empty description → Other"

    description_lower = description.lower().strip()

    for keyword, category in CATEGORIZATION_RULES:
        if keyword.lower() in description_lower:
            return f'Matched keyword "{keyword}" → {category}'

    if amount is not None and amount > 0:
        return "Positive amount with no keyword match → Salary & Income"

    return "No keyword matched → Other"


def bulk_categorize(descriptions: list[str], amounts: list[float] = None) -> list[str]:
    """
    Categorize a list of descriptions. Used for batch processing.

    Args:
        descriptions: List of merchant names / narrations
        amounts:      Corresponding list of amounts (optional)

    Returns:
        List of category names in the same order.
    """
    if amounts is None:
        amounts = [None] * len(descriptions)

    return [
        categorize_transaction(desc, amt)
        for desc, amt in zip(descriptions, amounts)
    ]
