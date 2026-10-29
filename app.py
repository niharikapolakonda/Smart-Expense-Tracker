from flask import Flask, render_template, request, redirect, url_for
from datetime import date
import os

app = Flask(__name__)

# Temporary in-memory storage (no database)
expenses = []
monthly_budget = 10000.0


@app.route("/", methods=["GET", "POST"])
def index():
    global monthly_budget

    if request.method == "POST":
        action = request.form.get("action", "add_expense")

        if action == "update_budget":
            try:
                new_budget = float(request.form.get("budget", 0))
                if new_budget >= 0:
                    monthly_budget = new_budget
            except (ValueError, TypeError):
                pass

            return redirect(url_for("index"))

        try:
            amount = float(request.form.get("amount", 0))
            category = request.form.get("category", "").strip()
            expense_date = request.form.get("date", str(date.today()))
            description = request.form.get("description", "").strip()

            if amount > 0 and category:
                expenses.append({
                    "id": len(expenses) + 1,
                    "amount": amount,
                    "category": category,
                    "date": expense_date,
                    "description": description
                })

        except (ValueError, TypeError):
            pass

        return redirect(url_for("index"))

    today = date.today()
    current_month = today.strftime("%Y-%m")

    monthly_expenses = [
        expense for expense in expenses
        if expense["date"].startswith(current_month)
    ]

    total_expenses = sum(item["amount"] for item in expenses)
    monthly_total = sum(item["amount"] for item in monthly_expenses)
    budget_remaining = monthly_budget - monthly_total

    return render_template(
        "index.html",
        expenses=expenses,
        total_expenses=total_expenses,
        monthly_total=monthly_total,
        monthly_budget=monthly_budget,
        budget_remaining=budget_remaining
    )


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    global expenses

    expenses = [
        expense for expense in expenses
        if expense["id"] != expense_id
    ]

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )