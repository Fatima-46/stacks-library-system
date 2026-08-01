# 📚 Stacks — Smart Library Management System (Web)

Full-stack web rebuild of my console C++ Library Management System — Flask, SQLite, REST API.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-DB-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

**[🔴 Live Demo](#)** *https://fatimasaleem.pythonanywhere.com



https://github.com/user-attachments/assets/94ffa0fc-a3c5-406a-8bcd-47b6d10e8670


---

## ✨ Features

- Add, search, and remove books from the catalog
- Register members and track outstanding fines
- Issue and return books with automatic due-date + late-fee calculation ($1/day, 14-day loan period)
- Live dashboard: titles on shelf, copies available, active loans, unpaid fines
- Full circulation history with status badges (Active / Overdue / Returned)
- A clean REST API you can call independently of the UI (see below)

## 🧱 Tech Stack

- **Backend:** Flask (Python), REST JSON API
- **Database:** SQLite (zero-config, file-based — perfect for a portfolio project, easy to swap for Postgres later)
- **Frontend:** Vanilla HTML/CSS/JS — no build step, no framework overhead
- **Server:** Gunicorn (production WSGI server) for deployment

## 🧠 What This Demonstrates

| Concept | Where |
|---|---|
| REST API design | `app.py` — resource-based routes, proper HTTP status codes (200/201/400/403/404/409) |
| Relational data modeling | `books`, `members`, `transactions` tables with foreign keys |
| Separation of concerns | Backend is pure API; frontend is a static SPA that consumes it |
| Business logic in the backend | Fine calculation, loan duration, and fine-cap enforcement all live server-side, not trusted to the client |
| Defensive API design | Every endpoint validates input and returns meaningful errors instead of crashing |

## 🚀 Run Locally

```bash
git clone https://github.com/Fatima-46/smart-library-management-web.git
cd smart-library-management-web
pip install -r requirements.txt
python app.py
```
Visit `http://localhost:5000`. The SQLite database (`library.db`) is created automatically on first run.

## 🌍 Deploy Free (Render)

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New +** → **Web Service** → connect this GitHub repo.
3. Render auto-detects `requirements.txt`. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Click **Create Web Service**. Render gives you a free live URL like `https://smart-library-management-web.onrender.com`.
5. Paste that URL into the **Live Demo** link at the top of this README.

> ⚠️ Free-tier Render services spin down after inactivity and take ~30–50s to wake up on the first request — this is normal, not a bug.

> ⚠️ Note on data persistence: Render's free tier has an ephemeral filesystem, so the SQLite file resets on redeploys/restarts. That's fine for a portfolio demo. For a project you want to keep data in permanently, add a free Render PostgreSQL instance and swap the `sqlite3` calls for `psycopg2` — a good "v2" to mention in interviews.

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/books` | List all books |
| POST | `/api/books` | Add a book `{id, title, author, genre, copies}` |
| DELETE | `/api/books/<id>` | Remove a book |
| GET | `/api/books/search?q=` | Search by title/author |
| GET | `/api/members` | List all members |
| POST | `/api/members` | Register a member `{id, name}` |
| POST | `/api/members/<id>/pay` | Pay off a fine `{amount}` |
| POST | `/api/issue` | Issue a book `{member_id, book_id}` |
| POST | `/api/return` | Return a book `{member_id, book_id}` |
| GET | `/api/transactions` | Full circulation history |
| GET | `/api/stats` | Dashboard summary numbers |

## 📂 Project Structure

```
.
├── app.py                # Flask app + REST API + SQLite models
├── templates/
│   └── index.html        # Single-page frontend
├── static/
│   ├── style.css
│   └── app.js
├── requirements.txt
├── Procfile               # for Render/Heroku-style deploys
└── README.md
```

## 📈 Possible Extensions

- Swap SQLite for PostgreSQL for persistent free-tier hosting
- Add JWT-based auth (Admin vs. Member roles)
- Add email/SMS reminders for due dates
- Containerize with Docker for a consistent deploy story

## 📄 License

MIT
