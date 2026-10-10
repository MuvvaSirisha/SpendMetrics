# Project Architecture

SpendSense is built using a modern, modular Python architecture, utilizing Streamlit for the presentation layer.

## Directory Layout
```
spendsense/
├── app.py                 # Streamlit entry point & router
├── pages/                 # UI Views (Dashboard, Analytics, etc.)
├── utils/                 # Core Business Logic (Ingestion, Categorization)
├── database/              # Data Access Layer (Connection, Schema, Queries)
├── tests/                 # Pytest Unit Tests
└── data/                  # Sample CSVs and SQLite DB file
```

## Architectural Patterns

1. **Separation of Concerns**: 
   - UI code (`pages/`) never writes raw SQL.
   - Database code (`database/`) never imports Streamlit.
   - Business logic (`utils/`) is completely decoupled and can be unit-tested independently.

2. **Adapter Pattern (Database)**:
   - `database/connection.py` decides at runtime whether to vend a SQLite connection or a MySQL connection based on `.env` configuration. The rest of the application is completely agnostic to the underlying database engine.

3. **Extract, Transform, Load (ETL)**:
   - The CSV upload process (`utils/ingestion.py`) follows a strict ETL pipeline:
     - **Extract**: Read raw bytes into Pandas.
     - **Transform**: Normalize column names, parse dates, enforce sign conventions, categorize.
     - **Load**: Insert clean dictionaries into the SQL database.

4. **Dynamic Page Routing**:
   - `app.py` uses `importlib` to load pages dynamically. This prevents the entire application from crashing if there is a syntax error in one specific page module, and speeds up initial load time.
