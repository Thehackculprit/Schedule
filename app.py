from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            is_booked INTEGER DEFAULT 0,
            candidate_name TEXT,
            candidate_email TEXT,
            candidate_phone TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        filter_date = request.form.get("filter_date")
        cursor.execute("SELECT * FROM slots WHERE date = ?", (filter_date,))
    else:
        cursor.execute("SELECT * FROM slots")

    slots = cursor.fetchall()
    conn.close()
    return render_template("index.html", slots=slots)


@app.route("/book/<int:slot_id>", methods=["POST"])
def book_slot(slot_id):
    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE slots SET is_booked=1, candidate_name=?, candidate_email=?, candidate_phone=? WHERE id=?",
        (name, email, phone, slot_id),
    )
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "admin@123":
            session["admin"] = True
            return redirect("/admin")
        else:
            return "Invalid credentials"
    return render_template("admin_login.html")


@app.route("/admin")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM slots")
    slots = cursor.fetchall()
    conn.close()
    return render_template("admin_dashboard.html", slots=slots)


@app.route("/admin/add_slot", methods=["POST"])
def add_slot():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    date = request.form["date"]
    time = request.form["time"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO slots (date, time, is_booked) VALUES (?, ?, 0)", (date, time)
    )
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/admin/delete_slot/<int:slot_id>", methods=["POST"])
def delete_slot(slot_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM slots WHERE id=?", (slot_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
