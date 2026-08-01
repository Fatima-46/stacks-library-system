"""
Smart Library Management System (Web Edition)
------------------------------------------------
Flask + SQLite REST API backend.

Endpoints:
  GET    /api/books                -> list all books
  POST   /api/books                -> add a book
  DELETE /api/books/<id>           -> remove a book
  GET    /api/books/search?q=...   -> search by title/author

  GET    /api/members              -> list all members
  POST   /api/members              -> register a member
  POST   /api/members/<id>/pay     -> pay off fine

  POST   /api/issue                -> issue a book to a member
  POST   /api/return               -> return a book
  GET    /api/transactions         -> full transaction history

  GET    /api/stats                -> dashboard summary numbers
"""

import sqlite3
import os
from datetime import date, timedelta
from flask import Flask, request, jsonify, g, render_template

DB_PATH = os.path.join(os.path.dirname(__file__), "library.db")
LOAN_DAYS = 14
FINE_PER_DAY = 1.0
MAX_UNPAID_FINE = 20.0

app = Flask(__name__)


# ---------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT DEFAULT 'General',
            total_copies INTEGER NOT NULL,
            available_copies INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS members (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            fine REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT NOT NULL,
            book_id TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            returned INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );
        """
    )
    db.commit()
    db.close()


# ---------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------
# Books API
# ---------------------------------------------------------------
@app.route("/api/books", methods=["GET"])
def list_books():
    db = get_db()
    rows = db.execute("SELECT * FROM books ORDER BY title").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/books", methods=["POST"])
def add_book():
    data = request.get_json(force=True)
    required = ["id", "title", "author", "copies"]
    for field in required:
        if not data.get(field) and data.get(field) != 0:
            return jsonify({"error": f"Missing field: {field}"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM books WHERE id = ?", (data["id"],)).fetchone()
    if existing:
        return jsonify({"error": f"Book ID '{data['id']}' already exists."}), 409

    copies = int(data["copies"])
    if copies < 1:
        return jsonify({"error": "Copies must be at least 1."}), 400

    db.execute(
        "INSERT INTO books (id, title, author, genre, total_copies, available_copies) VALUES (?,?,?,?,?,?)",
        (data["id"], data["title"], data["author"], data.get("genre", "General"), copies, copies),
    )
    db.commit()
    return jsonify({"message": "Book added successfully."}), 201


@app.route("/api/books/<book_id>", methods=["DELETE"])
def remove_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not row:
        return jsonify({"error": "Book not found."}), 404
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return jsonify({"message": "Book removed."})


@app.route("/api/books/search", methods=["GET"])
def search_books():
    q = request.args.get("q", "").strip().lower()
    db = get_db()
    rows = db.execute(
        "SELECT * FROM books WHERE lower(title) LIKE ? OR lower(author) LIKE ? ORDER BY title",
        (f"%{q}%", f"%{q}%"),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------
# Members API
# ---------------------------------------------------------------
@app.route("/api/members", methods=["GET"])
def list_members():
    db = get_db()
    rows = db.execute("SELECT * FROM members ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/members", methods=["POST"])
def add_member():
    data = request.get_json(force=True)
    if not data.get("id") or not data.get("name"):
        return jsonify({"error": "Both id and name are required."}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM members WHERE id = ?", (data["id"],)).fetchone()
    if existing:
        return jsonify({"error": f"Member ID '{data['id']}' already exists."}), 409

    db.execute("INSERT INTO members (id, name, fine) VALUES (?, ?, 0)", (data["id"], data["name"]))
    db.commit()
    return jsonify({"message": "Member registered successfully."}), 201


@app.route("/api/members/<member_id>/pay", methods=["POST"])
def pay_fine(member_id):
    data = request.get_json(force=True)
    amount = float(data.get("amount", 0))
    if amount <= 0:
        return jsonify({"error": "Amount must be positive."}), 400

    db = get_db()
    member = db.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if not member:
        return jsonify({"error": "Member not found."}), 404

    new_fine = max(0.0, member["fine"] - amount)
    db.execute("UPDATE members SET fine = ? WHERE id = ?", (new_fine, member_id))
    db.commit()
    return jsonify({"message": "Payment recorded.", "remaining_fine": round(new_fine, 2)})


# ---------------------------------------------------------------
# Issue / Return
# ---------------------------------------------------------------
@app.route("/api/issue", methods=["POST"])
def issue_book():
    data = request.get_json(force=True)
    member_id, book_id = data.get("member_id"), data.get("book_id")
    if not member_id or not book_id:
        return jsonify({"error": "member_id and book_id are required."}), 400

    db = get_db()
    member = db.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if not member:
        return jsonify({"error": "Member not found."}), 404
    if member["fine"] > MAX_UNPAID_FINE:
        return jsonify({"error": f"Member has unpaid fines over ${MAX_UNPAID_FINE:.2f}. Clear dues first."}), 403

    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        return jsonify({"error": "Book not found."}), 404
    if book["available_copies"] <= 0:
        return jsonify({"error": f"No copies available for '{book['title']}'."}), 409

    today = date.today()
    due = today + timedelta(days=LOAN_DAYS)

    db.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,))
    db.execute(
        "INSERT INTO transactions (member_id, book_id, issue_date, due_date, returned) VALUES (?,?,?,?,0)",
        (member_id, book_id, today.isoformat(), due.isoformat()),
    )
    db.commit()
    return jsonify({"message": f'Issued "{book["title"]}" to {member["name"]}.', "due_date": due.isoformat()}), 201


@app.route("/api/return", methods=["POST"])
def return_book():
    data = request.get_json(force=True)
    member_id, book_id = data.get("member_id"), data.get("book_id")
    if not member_id or not book_id:
        return jsonify({"error": "member_id and book_id are required."}), 400

    db = get_db()
    txn = db.execute(
        """SELECT * FROM transactions
           WHERE member_id = ? AND book_id = ? AND returned = 0
           ORDER BY id DESC LIMIT 1""",
        (member_id, book_id),
    ).fetchone()
    if not txn:
        return jsonify({"error": "No active loan found for this member/book."}), 404

    today = date.today()
    due = date.fromisoformat(txn["due_date"])
    fine_added = 0.0
    if today > due:
        late_days = (today - due).days
        fine_added = late_days * FINE_PER_DAY
        db.execute("UPDATE members SET fine = fine + ? WHERE id = ?", (fine_added, member_id))

    db.execute(
        "UPDATE transactions SET returned = 1, return_date = ? WHERE id = ?",
        (today.isoformat(), txn["id"]),
    )
    db.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (book_id,))
    db.commit()

    msg = "Returned on time. Thank you!" if fine_added == 0 else f"Returned late. Fine of ${fine_added:.2f} added."
    return jsonify({"message": msg, "fine_added": round(fine_added, 2)})


@app.route("/api/transactions", methods=["GET"])
def list_transactions():
    db = get_db()
    rows = db.execute(
        """SELECT t.*, m.name AS member_name, b.title AS book_title
           FROM transactions t
           JOIN members m ON t.member_id = m.id
           JOIN books b ON t.book_id = b.id
           ORDER BY t.id DESC"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/stats", methods=["GET"])
def stats():
    db = get_db()
    total_books = db.execute("SELECT COALESCE(SUM(total_copies),0) AS n FROM books").fetchone()["n"]
    available = db.execute("SELECT COALESCE(SUM(available_copies),0) AS n FROM books").fetchone()["n"]
    total_members = db.execute("SELECT COUNT(*) AS n FROM members").fetchone()["n"]
    active_loans = db.execute("SELECT COUNT(*) AS n FROM transactions WHERE returned = 0").fetchone()["n"]
    total_fines = db.execute("SELECT COALESCE(SUM(fine),0) AS n FROM members").fetchone()["n"]
    return jsonify(
        {
            "total_books": total_books,
            "available_books": available,
            "total_members": total_members,
            "active_loans": active_loans,
            "total_unpaid_fines": round(total_fines, 2),
        }
    )


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
