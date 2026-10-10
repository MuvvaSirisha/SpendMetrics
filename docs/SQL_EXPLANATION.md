# SQL Explanations

This document explains the key SQL concepts utilized in SpendSense.

## 1. Aggregation (`GROUP BY` and `SUM`)
Used extensively in the dashboard to calculate category totals.
```sql
SELECT category_name, ABS(SUM(amount)) AS total_spent
FROM transactions
WHERE amount < 0
GROUP BY category_name
ORDER BY total_spent DESC
```
*Concept*: `GROUP BY` collapses multiple rows sharing the same category into a single row. `SUM` calculates the total for that group.

## 2. Conditional Aggregation (`CASE WHEN`)
Used in the monthly summary to separate income and expenses in a single pass.
```sql
SELECT 
    strftime('%Y-%m', transaction_date) AS month,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) AS total_expenses,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS total_income
FROM transactions
GROUP BY month
```
*Concept*: `CASE WHEN` acts as an if/else statement inside the SQL sum function.

## 3. Left Joins and Subqueries (Budgets)
Used to show all budgets, even if nothing has been spent yet.
```sql
SELECT 
    b.category_name, 
    b.amount AS budget_amount,
    COALESCE(
        (SELECT ABS(SUM(t.amount)) 
         FROM transactions t 
         WHERE t.category_name = b.category_name 
         AND t.amount < 0), 0
    ) AS spent
FROM budgets b
```
*Concept*: The subquery dynamically calculates the spending for each budget row. `COALESCE` converts `NULL` (when no spending exists) to `0`.

## 4. Window Functions (`LAG`)
Used for month-over-month comparisons.
```sql
WITH monthly_totals AS (
    SELECT strftime('%Y-%m', transaction_date) AS month, SUM(ABS(amount)) as total
    FROM transactions WHERE amount < 0 GROUP BY month
)
SELECT 
    month, total,
    LAG(total) OVER (ORDER BY month) AS prev_month_total
FROM monthly_totals
```
*Concept*: `LAG` looks at the previous row's value. The `OVER` clause defines the ordering (by month) so the database knows which row is "previous". `WITH` creates a temporary result set (CTE) to make the query readable.
