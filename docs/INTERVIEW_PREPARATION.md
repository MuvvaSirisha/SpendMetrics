# Interview Preparation Guide

This document contains 20+ questions and answers to help you explain the SpendSense project in software engineering or data analytics interviews.

## General Project Overview
**1. What is SpendSense?**
SpendSense is a personal finance analytics application that I built from scratch. It allows users to upload their bank transaction CSVs, automatically categorizes expenses, tracks budgets, flags unusual spending, and provides interactive visualizations of their financial health. 

**2. Why did you build it?**
I wanted to build a practical, end-to-end project that applies Python, SQL, and data visualization. I avoided using complex frameworks like React or a separate backend, opting instead for Streamlit to handle the UI and routing, allowing me to focus on the core data processing and analytics logic.

## Python & Architecture
**3. How is the project structured?**
I used a modular design. `app.py` handles Streamlit routing. The `pages/` directory contains the UI for each dashboard view. The `utils/` directory contains business logic (ingestion, categorization, anomaly detection) independent of the UI. Finally, `database/` encapsulates all SQL queries and schema definitions.

**4. How does the CSV ingestion pipeline work?**
When a user uploads a CSV, `utils/ingestion.py` reads it into a Pandas DataFrame. It uses a flexible alias-matching system to identify standard columns (like "Date", "Description", "Amount") regardless of the bank's naming conventions. It then validates dates, standardizes the sign convention (negative for expenses), checks for duplicates using a hash set, and returns clean rows for insertion.

**5. How does the categorization engine work?**
It uses a transparent, rule-based approach. In `utils/categorization.py`, I maintain an ordered list of `(keyword, category)` tuples. For each transaction, the system checks the description against these keywords in order. If there's a match, it assigns the category. If not, it falls back to "Other" or "Salary & Income" based on the amount sign. This is faster and more explainable than an ML model for personal finance.

**6. What are the advantages of Streamlit?**
Streamlit allows you to build interactive web apps purely in Python. It handles the frontend React components automatically. It was perfect for this project because it let me quickly build a data-rich dashboard without needing to write HTML/CSS/JS or set up a REST API.

## Database & SQL
**7. Why did you use SQLite by default but support MySQL?**
SQLite is embedded and requires zero setup, making the app immediately runnable for anyone who clones the repository. However, SQLite doesn't handle concurrent writes well. By using the Adapter pattern in `database/connection.py`, I designed the app so it can easily switch to a robust MySQL database just by changing a `.env` variable.

**8. Explain the database schema.**
The schema is normalized. The main `transactions` table stores the core data (date, description, amount, category_name). I have a `budgets` table to track monthly limits, and an `import_history` table for auditing uploads. 

**9. How do you prevent SQL injection?**
I exclusively used parameterized queries (e.g., `cursor.execute("SELECT * FROM table WHERE id = ?", (id,))`). This ensures that user input is treated as literal values, not executable SQL code, completely eliminating SQL injection vulnerabilities.

**10. Can you explain a complex SQL query you used?**
In `queries.get_month_over_month_comparison()`, I used a Common Table Expression (CTE) to first aggregate total expenses by month. Then, in the main query, I used the `LAG()` window function to fetch the previous month's total on the same row, allowing me to easily calculate the month-over-month change in spending.

**11. Why do you use SQL for aggregation instead of Pandas?**
While Pandas is great for data manipulation, database engines are highly optimized for aggregation. Using SQL `GROUP BY` to sum category spending directly in the database is much more memory-efficient than pulling thousands of raw rows into Python and grouping them in Pandas.

## Data Processing & Analytics
**12. How does the recurring payment detector work?**
In `utils/recurring_detector.py`, the system groups transactions by merchant. It then looks for groups with at least 2 occurrences where the amounts are identical or highly similar. It calculates the average time interval (in days) between these transactions. If the interval matches a standard pattern (e.g., ~30 days), it flags it as a potential monthly subscription.

**13. How does the unusual spending alert work?**
`utils/anomaly_detector.py` calculates the historical average spending for each category. If a single transaction exceeds this average by a specific multiplier (e.g., 3x), and there's enough historical data to establish a valid baseline, it flags the transaction as unusual.

**14. How do you handle dates from different bank CSV formats?**
I used the `python-dateutil` library. Its `parser.parse()` function is incredibly robust and can automatically interpret varying formats like "DD/MM/YYYY", "YYYY-MM-DD", or "DD-MMM-YYYY" without needing explicit format strings for every bank.

**15. How do you handle duplicate transaction uploads?**
During ingestion, the app queries the database for existing transaction hashes (a combination of Date, Description, and Amount). Before processing a new row, it checks if this hash already exists. If it does, the row is skipped and flagged as a duplicate in the import summary.

## Testing & Best Practices
**16. How did you test the application?**
I wrote automated tests using `pytest`. I focused on unit testing the core business logic: the categorization rules, the amount/date parsing in the ingestion pipeline, and the sign conversion logic. This ensures that the foundational data transformations are reliable.

**17. What is the `.env.example` file for?**
It's a template for environment variables. It shows developers what configuration keys the app needs (like DB connection strings) without exposing actual passwords, since the real `.env` file is excluded from Git via `.gitignore`.

**18. Why did you use `sqlite3.Row` factory?**
By default, SQLite returns rows as tuples (e.g., `row[2]`). By setting `conn.row_factory = sqlite3.Row`, the rows behave like dictionaries, allowing me to access columns by name (e.g., `row["amount"]`). This makes the code much more readable and robust against schema changes.

**19. What were the biggest challenges you faced?**
Handling the varying CSV formats from different banks was challenging. Banks use different column names and date formats, and some use single amount columns with negative signs while others use separate Debit/Credit columns. Building a flexible ingestion pipeline to handle these variations was a great learning experience.

**20. How would you scale this application for multiple users?**
Currently, it's a single-user local app. To scale it, I would need to add an `users` table to the database, add a `user_id` foreign key to all other tables (transactions, budgets), implement authentication (e.g., JWT or OAuth), and convert the architecture to a client-server model (like React + FastAPI) to handle concurrent user sessions efficiently.
