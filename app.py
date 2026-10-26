from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = "smart-expense-tracker-local-key"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    with connect() as conn:
        # New databases use this schema.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Other',
                amount REAL NOT NULL CHECK(amount > 0),
                expense_date TEXT NOT NULL,
                description TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS budget (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                amount REAL NOT NULL DEFAULT 0
            )
        """)

        # Migrate older database tables safely.
        expense_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(expenses)"
            ).fetchall()
        }

        if "name" not in expense_columns:
            conn.execute(
                "ALTER TABLE expenses ADD COLUMN name TEXT NOT NULL DEFAULT 'Expense'"
            )

        if "category" not in expense_columns:
            conn.execute(
                "ALTER TABLE expenses ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'"
            )

        if "amount" not in expense_columns:
            conn.execute(
                "ALTER TABLE expenses ADD COLUMN amount REAL NOT NULL DEFAULT 0"
            )

        if "expense_date" not in expense_columns:
            conn.execute(
                "ALTER TABLE expenses ADD COLUMN expense_date TEXT NOT NULL DEFAULT '2026-01-01'"
            )

        if "description" not in expense_columns:
            conn.execute(
                "ALTER TABLE expenses ADD COLUMN description TEXT DEFAULT ''"
            )

        budget_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(budget)"
            ).fetchall()
        }

        if "amount" not in budget_columns:
            conn.execute(
                "ALTER TABLE budget ADD COLUMN amount REAL NOT NULL DEFAULT 0"
            )

        conn.execute("""
            INSERT OR IGNORE INTO budget (id, amount)
            VALUES (1, 0)
        """)


@app.route("/", methods=["GET"])
def home():
    with connect() as conn:
        expenses = conn.execute("""
            SELECT * FROM expenses
            ORDER BY expense_date DESC, id DESC
        """).fetchall()

        total = conn.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
        """).fetchone()[0]

        budget_row = conn.execute(
            "SELECT amount FROM budget WHERE id = 1"
        ).fetchone()

        budget_amount = budget_row["amount"] if budget_row else 0

        category_totals = conn.execute("""
            SELECT category, SUM(amount) AS total
            FROM expenses
            GROUP BY category
            ORDER BY total DESC
        """).fetchall()

    remaining = budget_amount - total

    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        budget=budget_amount,
        remaining=remaining,
        category_totals=category_totals,
        today=date.today().isoformat()
    )


@app.route("/add", methods=["POST"])
def add_expense():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Other").strip()
    amount_text = request.form.get("amount", "").strip()
    expense_date = request.form.get("expense_date", "").strip()
    description = request.form.get("description", "").strip()

    if not name or not amount_text:
        flash("Please enter an expense name and amount.", "error")
        return redirect(url_for("home"))

    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid amount greater than zero.", "error")
        return redirect(url_for("home"))

    if not expense_date:
        expense_date = date.today().isoformat()

    try:
        with connect() as conn:
            conn.execute("""
                INSERT INTO expenses
                (name, category, amount, expense_date, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                name, category or "Other", amount,
                expense_date, description
            ))
        flash("Expense added successfully!", "success")
    except sqlite3.Error:
        app.logger.exception("Could not add expense")
        flash("Could not save the expense. Check the terminal for details.", "error")

    return redirect(url_for("home"))


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    with connect() as conn:
        conn.execute(
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        )

    flash("Expense deleted.", "success")
    return redirect(url_for("home"))


@app.route("/budget", methods=["POST"])
def set_budget():
    budget_text = request.form.get("budget", "").strip()

    try:
        amount = float(budget_text)
        if amount < 0:
            raise ValueError
    except ValueError:
        flash("Enter a valid budget amount (zero or more).", "error")
        return redirect(url_for("home"))

    with connect() as conn:
        conn.execute("""
            INSERT INTO budget (id, amount)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET amount = excluded.amount
        """, (amount,))

    flash("Monthly budget updated.", "success")
    return redirect(url_for("home"))


@app.route("/expenses", methods=["GET"])
def get_expenses():
    # Optional backend endpoint for checking stored records.
    with connect() as conn:
        rows = conn.execute("""
            SELECT id, name, category, amount, expense_date, description
            FROM expenses
            ORDER BY expense_date DESC, id DESC
        """).fetchall()

    return {
        "expenses": [dict(row) for row in rows]
    }


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)