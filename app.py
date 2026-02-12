from flask import Flask, render_template, request, redirect, session, url_for
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "finance_secret_key"

app.config["MONGO_URI"] = "mongodb://localhost:27017/finance_demo_db"
mongo = PyMongo(app)

users = mongo.db.users
transactions = mongo.db.transactions


@app.route("/", methods=["GET", "POST"])
def login():
    msg = None
    if request.method == "POST":
        user = users.find_one({"email": request.form["email"]})
        if user and check_password_hash(user["password"], request.form["password"]):
            session["user"] = {
                "name": user["name"],
                "email": user["email"]
            }
            return redirect("/dashboard")
        else:
            msg = "Invalid email or password."
    return render_template("login.html", msg=msg)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        users.insert_one({
            "name": request.form["name"],
            "email": request.form["email"],
            "password": generate_password_hash(request.form["password"])
        })
        return redirect("/")
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    month = request.args.get("month")
    year = request.args.get("year")

    query = {"user": session["user"]}

    if month and year:
        start = f"{year}-{month}-01"
        end = f"{year}-{month}-31"
        query["date"] = {"$gte": start, "$lte": end}

    txns = list(transactions.find(query).sort("date", -1))

    income = sum(t["amount"] for t in txns if t["type"] == "Income")
    expenses = sum(t["amount"] for t in txns if t["type"] == "Expense")
    balance = income - expenses

    savings_rate = round(((income - expenses) / income) * 100, 1) if income else 0

    return render_template(
        "dashboard.html",
        transactions=txns,
        income=income,
        expenses=expenses,
        balance=balance,
        savings_rate=savings_rate
    )


@app.route("/add", methods=["GET", "POST"])
def add_transaction():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        transactions.insert_one({
            "user": session["user"],
            "type": request.form["type"],
            "amount": float(request.form["amount"]),
            "category": request.form["category"],
            "account": request.form["account"],
            "description": request.form["description"],
            "date": request.form["date"]
        })
        return redirect("/dashboard")

    return render_template("add_transaction.html", today=datetime.today().strftime("%Y-%m-%d"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# Change password route
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user" not in session:
        return redirect("/")
    msg = None
    if request.method == "POST":
        user = users.find_one({"email": session["user"]})
        old = request.form["old_password"]
        new = request.form["new_password"]
        confirm = request.form["confirm_password"]
        if not check_password_hash(user["password"], old):
            msg = "Old password is incorrect."
        elif new != confirm:
            msg = "New passwords do not match."
        else:
            users.update_one({"email": session["user"]}, {"$set": {"password": generate_password_hash(new)}})
            msg = "Password changed successfully."
    return render_template("change_password.html", msg=msg)


if __name__ == "__main__":
    app.run(debug=True)
