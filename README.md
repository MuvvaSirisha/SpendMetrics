# 💰 SpendSense — Personal Finance Analytics Dashboard

SpendSense is a personal finance analytics application built with Python and Streamlit.
Upload your bank transaction CSV, categorize your spending, set budgets, and see interactive
charts that help you understand where your money goes.

> **Learning Project** — Built step-by-step for a college student learning Python, SQL,
> data analytics, and software development. Every file is commented and explained.

---

## 📋 Table of Contents

1. [Features](#features)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Installation](#installation)
5. [Running the App](#running-the-app)
6. [Using Sample Data](#using-sample-data)
7. [CSV Format](#csv-format)
8. [Database Setup](#database-setup)
9. [Running Tests](#running-tests)
10. [Application Flow](#application-flow)
11. [Limitations](#limitations)
12. [Interview Preparation](#interview-preparation)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Dashboard** | Total spending, income, cash flow, category charts, monthly trends |
| 💳 **Transactions** | Upload CSV, preview, validate, search, filter, edit, delete |
| 📈 **Spending Analytics** | Category breakdown, merchant rankings, daily/monthly trends |
| 🔁 **Recurring Payments** | Detect subscriptions and regular payments automatically |
| 🎯 **Budgets** | Set monthly budgets by category; track usage with progress bars |
| ⚙️ **Settings** | Configure thresholds, manage data, clear database |

---

## 🛠️ Technology Stack

| Technology | Role |
|------------|------|
| **Python 3.9+** | Application logic |
| **Streamlit** | Complete web UI — no separate frontend |
| **Pandas** | CSV reading, data cleaning, transformations |
| **NumPy** | Numerical calculations |
| **Plotly** | Interactive bar, line, pie, and scatter charts |
| **SQLite** | Default local database (no configuration needed) |
| **MySQL** | Optional production database |
| **python-dotenv** | Reads `.env` credentials file |
| **pytest** | Automated tests |

---

## 📁 Project Structure

```
spendsense/
├── app.py                    # Entry point — run this with Streamlit
├── requirements.txt          # All dependencies
├── .env.example              # Template for database credentials
├── .gitignore                # Keeps secrets and generated files out of Git
├── README.md                 # This file
│
├── pages/                    # One file per page
│   ├── dashboard.py          # Overview Dashboard
│   ├── transactions.py       # Transaction management
│   ├── analytics.py          # Spending Analytics
│   ├── recurring.py          # Recurring Payment Detection
│   ├── budgets.py            # Budget Tracking
│   └── settings.py           # Settings & Data Management
│
├── utils/                    # Reusable logic (no UI code here)
│   ├── config.py             # Colors, categories, DB config, constants
│   ├── ingestion.py          # CSV reading, validation, cleaning
│   ├── categorization.py     # Rule-based transaction categorization
│   ├── analytics.py          # Spending calculations and summaries
│   ├── recurring_detector.py # Recurring payment detection logic
│   └── anomaly_detector.py   # Unusual spending detection
│
├── database/                 # Database layer (no UI code here)
│   ├── connection.py         # Connect to SQLite or MySQL
│   ├── schema.py             # Create tables if they don't exist
│   └── queries.py            # All SQL queries as Python functions
│
├── data/
│   └── sample_transactions.csv   # 90-row synthetic demo data
│
└── tests/                    # Automated tests
    ├── test_ingestion.py
    ├── test_categorization.py
    ├── test_analytics.py
    ├── test_budgets.py
    └── test_recurring.py
```

---

## 🚀 Installation

### Step 1 — Clone / Download the project

If you're starting fresh, make sure you're inside the `spendsense/` folder.

### Step 2 — Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

> **Why?** A virtual environment isolates the project's packages from your
> system Python, preventing version conflicts.

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs: Streamlit, Pandas, NumPy, Plotly, mysql-connector-python,
python-dotenv, pytest, and python-dateutil.

### Step 4 — Configure environment (optional)

```bash
# Copy the template
copy .env.example .env      # Windows
cp .env.example .env        # macOS / Linux
```

Edit `.env` if you want to use MySQL. Leave it as-is to use SQLite (default).

---

## ▶️ Running the App

```bash
streamlit run app.py
```

Streamlit will print a URL like `http://localhost:8501`.
Open it in your browser.

---

## 📂 Using Sample Data

The file `data/sample_transactions.csv` contains 90 synthetic transactions
spanning September–November 2024.

Two ways to load it:
1. Go to **Transactions** → click **"Load Sample Data"**
2. Go to **Transactions** → upload `data/sample_transactions.csv`

---

## 📄 CSV Format

SpendSense accepts CSV files with these columns:

### Minimum required columns:
| Column | Example | Notes |
|--------|---------|-------|
| `date` | `2024-09-15` | Any common date format |
| `description` | `Swiggy Food Order` | Merchant or transaction name |
| `amount` | `-450.00` | Negative = expense, Positive = income |

### Optional columns:
| Column | Example | Notes |
|--------|---------|-------|
| `type` | `debit` or `credit` | Overrides sign detection |
| `category` | `Food & Dining` | Pre-assigned category |

### Column name aliases supported:
- `date` → also: `transaction_date`, `txn_date`, `value_date`
- `description` → also: `narration`, `particulars`, `merchant`
- `amount` → also: `amt`, `transaction_amount`

Download the sample CSV from the Transactions page for reference.

---

## 🗄️ Database Setup

### Option A — SQLite (Default, no setup needed)

SQLite is used automatically. The database file is created at
`data/spendsense.db` the first time you run the app.

```
USE_MYSQL=false   ← (default in .env)
```

### Option B — MySQL

1. Install MySQL 8.0+
2. Create a database: `CREATE DATABASE spendsense;`
3. Edit `.env`:
```
USE_MYSQL=true
DB_HOST=localhost
DB_PORT=3306
DB_NAME=spendsense
DB_USER=your_username
DB_PASSWORD=your_password
```

The app creates all tables automatically on first run.

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Or run a specific test file:
```bash
pytest tests/test_categorization.py -v
```

---

## 🔄 Application Flow

```
User uploads CSV
       ↓
ingestion.py — reads, validates, cleans the CSV
       ↓
categorization.py — assigns categories using keyword rules
       ↓
database/queries.py — saves to SQLite or MySQL
       ↓
SQL queries — aggregate spending by category, month, merchant
       ↓
Pandas — additional transformations (trends, comparisons)
       ↓
Plotly — renders interactive charts
       ↓
Streamlit pages — displays everything in the browser
```

---

## ⚠️ Limitations

- **Single-user only** — no login system; all data is shared on the same machine
- **No bank connection** — you must upload a CSV manually
- **Rule-based categorization** — not ML; some transactions may need manual correction
- **SQLite concurrency** — SQLite doesn't support multiple simultaneous writers
- **No real-time data** — transactions are static once imported

---

## 💡 Interview Preparation

See the Streamlit app → **Settings** page for a full Q&A guide covering:
- Python module design
- SQL joins, GROUP BY, CTEs, window functions
- Pandas vs SQL responsibilities
- Streamlit architecture
- Database design and normalization
- Data validation strategies
