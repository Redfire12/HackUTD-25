from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from textblob import TextBlob
from fastapi.middleware.cors import CORSMiddleware
import openai, os, logging
from datetime import datetime
from pathlib import Path
from html import escape
from typing import Optional, List, Dict
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, create_engine, func, select
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError
from urllib.parse import quote

# ------------------------------------------------
# app initialization
# ------------------------------------------------
app = FastAPI(title="HackUTD Backend", version="1.1.0")

# ------------------------------------------------
# enable CORS for frontend integration
# ------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow all origins (safe for demo)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------
# logging configuration
# ------------------------------------------------
LOG_FILE = "server.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.sqlite3'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    feedback_entries = relationship("FeedbackEntry", back_populates="user")


class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    text = Column(Text, nullable=False)
    sentiment = Column(Float, nullable=False)
    label = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedback_entries")


Base.metadata.create_all(bind=engine)


def get_user(session, username: str) -> Optional[User]:
    if not username:
        return None
    username_lower = username.lower()
    result = session.execute(
        select(User).where(func.lower(User.username) == username_lower)
    )
    return result.scalar_one_or_none()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    logging.info(f"{request.method} {request.url.path} -> {response.status_code} [{process_time:.3f}s]")
    return response

# ------------------------------------------------
# load OpenAI key (optional for now)
# ------------------------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------------------------------------
# root route
# ------------------------------------------------
@app.get("/")
def root():
    logging.info("Root endpoint accessed")
    return {
        "status": "ok",
        "message": "Backend is running. Go to /docs to test endpoints."
    }

# ------------------------------------------------
# feedback capture page
# ------------------------------------------------
@app.get("/feedback", response_class=HTMLResponse)
def feedback_page():
    logging.info("/feedback page served")
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Customer Feedback Sentiment</title>
        <style>
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
          }
          .container {
            width: min(620px, 100%);
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 2.5rem 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.75rem;
            box-shadow: 0 30px 60px rgba(15, 23, 42, 0.45);
          }
          h1 { margin: 0; font-size: 2.25rem; }
          .user-info {
            margin: 0;
            font-size: 0.95rem;
            color: #94a3b8;
          }
          .user-info strong { color: #38bdf8; }
          .user-info a {
            color: #38bdf8;
            text-decoration: none;
            font-weight: 600;
          }
          .user-info a:hover { text-decoration: underline; }
          label {
            font-weight: 600;
            display: block;
            margin-bottom: 0.75rem;
          }
          textarea {
            width: 100%;
            min-height: 170px;
            padding: 1rem;
            font-size: 1rem;
            border-radius: 14px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            background: rgba(15, 23, 42, 0.6);
            color: inherit;
            resize: vertical;
          }
          textarea:focus {
            outline: 2px solid #38bdf8;
            border-color: transparent;
          }
          button {
            align-self: flex-start;
            background: #38bdf8;
            color: #0f172a;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            padding: 0.85rem 1.6rem;
            cursor: pointer;
            transition: transform 0.1s ease, box-shadow 0.1s ease;
          }
          button:hover { transform: translateY(-1px); box-shadow: 0 18px 36px rgba(56, 189, 248, 0.35); }
          button:active { transform: translateY(0); box-shadow: none; }
          .result {
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid rgba(148, 163, 184, 0.25);
            background: rgba(15, 23, 42, 0.35);
            display: none;
            gap: 0.5rem;
          }
          .result.visible { display: flex; flex-direction: column; }
          .result h2 { margin: 0 0 0.25rem; font-size: 1.25rem; }
          .sentiment-label { text-transform: capitalize; font-weight: 700; }
          .status { font-size: 0.9rem; color: #94a3b8; }
          .history {
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.25);
            background: rgba(15, 23, 42, 0.35);
            padding: 1rem;
            display: none;
            flex-direction: column;
            gap: 1rem;
          }
          .history.visible { display: flex; }
          .history h2 { margin: 0; font-size: 1.1rem; }
          .history__list {
            margin: 0;
            padding: 0;
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
          }
          .history__item {
            border-radius: 10px;
            border: 1px solid rgba(148, 163, 184, 0.25);
            padding: 0.8rem;
            background: rgba(15, 23, 42, 0.55);
          }
          .history__item p { margin: 0.2rem 0; }
          .history__item time {
            font-size: 0.85rem;
            color: #94a3b8;
          }
          .history__empty {
            font-size: 0.95rem;
            color: #94a3b8;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <header>
            <h1>Customer Sentiment Analyzer</h1>
            <p class="status">Submit feedback to detect sentiment in real time.</p>
            <p id="user-info" class="user-info"></p>
          </header>
          <form id="feedback-form">
            <label for="feedback-input">Customer Feedback</label>
            <textarea id="feedback-input" name="feedback" placeholder="Describe the customer feedback here..." required></textarea>
            <button type="submit">Analyze Sentiment</button>
          </form>
          <section id="result" class="result" aria-live="polite"></section>
          <section id="history" class="history" aria-live="polite">
            <div>
              <h2>Recent Feedback</h2>
              <p id="history-empty" class="history__empty">No feedback stored yet.</p>
            </div>
            <ul id="history-list" class="history__list"></ul>
          </section>
        </div>

        <script>
          const form = document.getElementById('feedback-form');
          const textarea = document.getElementById('feedback-input');
          const resultPanel = document.getElementById('result');
          const historyPanel = document.getElementById('history');
          const historyList = document.getElementById('history-list');
          const historyEmpty = document.getElementById('history-empty');
          const userInfo = document.getElementById('user-info');

          const params = new URLSearchParams(window.location.search);
          const currentUser = params.get('user');

          if (currentUser) {
            userInfo.innerHTML = `Signed in as <strong>${currentUser}</strong> • <a href="/stats?user=${encodeURIComponent(currentUser)}">View stats</a> • <a href="/login">Sign out</a>`;
            loadHistory(currentUser);
          } else {
            userInfo.innerHTML = 'Not signed in. <a href="/login">Go to login</a>';
          }

          async function loadHistory(user) {
            try {
              const response = await fetch(`/feedback/history/${user}`);
              if (!response.ok) throw new Error('Unable to fetch history');
              const data = await response.json();
              renderHistory(data.entries || []);
            } catch (error) {
              console.error(error);
            }
          }

          function renderHistory(entries) {
            if (!entries.length) {
              historyPanel.classList.remove('visible');
              historyEmpty.style.display = 'block';
              historyList.innerHTML = '';
              return;
            }

            historyPanel.classList.add('visible');
            historyEmpty.style.display = 'none';
            historyList.innerHTML = entries
              .slice()
              .reverse()
              .map(entry => `
                <li class="history__item">
                  <p><strong>${entry.label}</strong> • Score: ${entry.sentiment.toFixed(3)}</p>
                  <p>${entry.text}</p>
                  <time>${new Date(entry.timestamp).toLocaleString()}</time>
                </li>
              `)
              .join('');
          }

          form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const text = textarea.value.trim();
            if (!text) return;

            resultPanel.className = 'result visible';
            resultPanel.innerHTML = '<p class="status">Analyzing sentiment...</p>';

            try {
              const payload = { text };
              if (currentUser) payload.user = currentUser;

              const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
              });

              if (!response.ok) throw new Error('Request failed');

              const data = await response.json();
              resultPanel.innerHTML = `
                <h2>Analysis Result</h2>
                <p>Label: <span class="sentiment-label">${data.label}</span></p>
                <p>Score: ${data.sentiment.toFixed(3)}</p>
              `;

              if (currentUser) {
                loadHistory(currentUser);
              }
            } catch (error) {
              console.error(error);
              resultPanel.innerHTML = '<p class="status">Something went wrong. Please try again.</p>';
            }
          });
        </script>
      </body>
    </html>
    """


# ------------------------------------------------
# mock login/signup portal
# ------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
def login_page():
    logging.info("/login page served")
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Sign In</title>
        <style>
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0f172a;
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
          }
          .card {
            width: min(420px, 100%);
            background: rgba(17, 24, 39, 0.92);
            border-radius: 18px;
            padding: 2.5rem 2rem 2rem;
            border: 1px solid rgba(148, 163, 184, 0.2);
            box-shadow: 0 35px 70px rgba(15, 23, 42, 0.55);
            display: grid;
            gap: 1.75rem;
          }
          h1 { margin: 0; font-size: 2.1rem; letter-spacing: -0.02em; }
          label {
            display: block;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
          }
          input {
            width: 100%;
            padding: 0.9rem 1rem;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            background: rgba(15, 23, 42, 0.7);
            color: inherit;
            font-size: 1rem;
          }
          input:focus {
            outline: 2px solid #38bdf8;
            border-color: transparent;
          }
          .btn {
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            border: none;
            border-radius: 12px;
            color: #0f172a;
            font-weight: 700;
            font-size: 1rem;
            padding: 0.9rem 1.4rem;
            cursor: pointer;
            transition: transform 0.1s ease, box-shadow 0.1s ease;
          }
          .btn:hover { transform: translateY(-1px); box-shadow: 0 20px 36px rgba(56, 189, 248, 0.35); }
          .btn:active { transform: translateY(0); box-shadow: none; }
          .status {
            min-height: 1.6rem;
            font-size: 0.95rem;
            margin: -0.5rem 0 0;
          }
          .status.success { color: #4ade80; }
          .status.error { color: #f87171; }
          .hint {
            font-size: 0.9rem;
            color: #94a3b8;
          }
          .hint strong { color: #38bdf8; }
          .footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9rem;
            color: #94a3b8;
          }
          .footer a {
            color: #38bdf8;
            font-weight: 600;
            text-decoration: none;
          }
          .footer a:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <div class="card">
          <header>
            <h1>Welcome back</h1>
            <p class="hint">Use <strong>demo</strong> / <strong>secret123</strong>, or the credentials you signed up with.</p>
          </header>
          <form id="login-form">
            <div>
              <label for="login-username">Username</label>
              <input id="login-username" name="username" autocomplete="username" required />
            </div>
            <div>
              <label for="login-password">Password</label>
              <input id="login-password" name="password" type="password" autocomplete="current-password" required />
            </div>
            <button type="submit" class="btn">Sign In</button>
          </form>
          <p id="login-status" class="status" aria-live="polite"></p>
          <div class="footer">
            <span>New here?</span>
            <a href="/signup">Create an account</a>
          </div>
        </div>

        <script>
          const form = document.getElementById('login-form');
          const statusEl = document.getElementById('login-status');

          form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const data = Object.fromEntries(new FormData(form).entries());

            statusEl.textContent = 'Checking credentials...';
            statusEl.className = 'status';

            try {
              const response = await fetch('/mock-login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
              });

              const result = await response.json();

              if (!response.ok || !result.success) {
                statusEl.textContent = result.message || 'Invalid username or password.';
                statusEl.className = 'status error';
                return;
              }

              statusEl.textContent = result.message;
              statusEl.className = 'status success';

              setTimeout(() => {
                window.location.href = `/feedback?user=${encodeURIComponent(result.user)}`;
              }, 800);
            } catch (error) {
              console.error(error);
              statusEl.textContent = 'Something went wrong. Try again.';
              statusEl.className = 'status error';
            }
          });
        </script>
      </body>
    </html>
    """


@app.get("/signup", response_class=HTMLResponse)
def signup_page():
    logging.info("/signup page served")
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Sign Up</title>
        <style>
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0f172a;
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
          }
          .card {
            width: min(440px, 100%);
            background: rgba(17, 24, 39, 0.92);
            border-radius: 18px;
            padding: 2.6rem 2.1rem 2.2rem;
            border: 1px solid rgba(148, 163, 184, 0.2);
            box-shadow: 0 35px 70px rgba(15, 23, 42, 0.55);
            display: grid;
            gap: 1.75rem;
          }
          h1 { margin: 0; font-size: 2.05rem; letter-spacing: -0.02em; }
          label {
            display: block;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
          }
          input {
            width: 100%;
            padding: 0.9rem 1rem;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            background: rgba(15, 23, 42, 0.7);
            color: inherit;
            font-size: 1rem;
          }
          input:focus {
            outline: 2px solid #38bdf8;
            border-color: transparent;
          }
          .btn {
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            border: none;
            border-radius: 12px;
            color: #0f172a;
            font-weight: 700;
            font-size: 1rem;
            padding: 0.9rem 1.4rem;
            cursor: pointer;
            transition: transform 0.1s ease, box-shadow 0.1s ease;
          }
          .btn:hover { transform: translateY(-1px); box-shadow: 0 20px 36px rgba(56, 189, 248, 0.35); }
          .btn:active { transform: translateY(0); box-shadow: none; }
          .status {
            min-height: 1.6rem;
            font-size: 0.95rem;
            margin: -0.5rem 0 0;
          }
          .status.success { color: #4ade80; }
          .status.error { color: #f87171; }
          .footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9rem;
            color: #94a3b8;
          }
          .footer a {
            color: #38bdf8;
            font-weight: 600;
            text-decoration: none;
          }
          .footer a:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <div class="card">
          <header>
            <h1>Create your account</h1>
            <p>Choose any username and password. We'll store it in-memory for this demo.</p>
          </header>
          <form id="signup-form">
            <div>
              <label for="signup-username">Username</label>
              <input id="signup-username" name="username" autocomplete="username" required />
            </div>
            <div>
              <label for="signup-password">Password</label>
              <input id="signup-password" name="password" type="password" autocomplete="new-password" required />
            </div>
            <div>
              <label for="signup-confirm">Confirm Password</label>
              <input id="signup-confirm" name="confirm" type="password" autocomplete="new-password" required />
            </div>
            <button type="submit" class="btn">Sign Up</button>
          </form>
          <p id="signup-status" class="status" aria-live="polite"></p>
          <div class="footer">
            <span>Already registered?</span>
            <a href="/login">Back to sign in</a>
          </div>
        </div>

        <script>
          const form = document.getElementById('signup-form');
          const statusEl = document.getElementById('signup-status');

          form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const data = Object.fromEntries(new FormData(form).entries());

            statusEl.textContent = 'Creating account...';
            statusEl.className = 'status';

            try {
              const response = await fetch('/mock-signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
              });

              const result = await response.json();

              if (!response.ok || !result.success) {
                statusEl.textContent = result.message || 'Unable to create account.';
                statusEl.className = 'status error';
                return;
              }

              statusEl.textContent = result.message;
              statusEl.className = 'status success';

              setTimeout(() => {
                window.location.href = `/feedback?user=${encodeURIComponent(result.user)}`;
              }, 900);
            } catch (error) {
              console.error(error);
              statusEl.textContent = 'Something went wrong. Try again.';
              statusEl.className = 'status error';
            }
          });
        </script>
      </body>
    </html>
    """


@app.post("/mock-login")
def mock_login(credentials: dict):
    username = credentials.get("username", "").strip()
    password = credentials.get("password", "")

    with SessionLocal() as session:
        user = get_user(session, username)
        valid = user is not None and user.password == password
        logging.info(
            f"/mock-login attempt user='{username}' -> {'success' if valid else 'failure'}"
        )

        if valid:
            return {
                "success": True,
                "message": f"Welcome back, {user.username}!",
                "user": user.username,
            }

    return {"success": False, "message": "Invalid username or password."}


@app.post("/mock-signup")
def mock_signup(credentials: dict):
    username = credentials.get("username", "").strip()
    password = credentials.get("password", "")
    confirm = credentials.get("confirm", "")

    if not username or not password:
        return {"success": False, "message": "Username and password are required."}

    if password != confirm:
        return {"success": False, "message": "Passwords do not match."}

    with SessionLocal() as session:
        existing = get_user(session, username)
        if existing:
            return {"success": False, "message": "Username already taken."}

        user = User(username=username, password=password)
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return {"success": False, "message": "Username already taken."}

        logging.info(f"/mock-signup new user='{user.username}'")
        return {
            "success": True,
            "message": f"Account created! Welcome, {user.username}.",
            "user": user.username,
        }

# ------------------------------------------------
# sentiment analysis endpoint
# ------------------------------------------------
class Feedback(BaseModel):
    text: str
    user: Optional[str] = None

@app.post("/analyze")
def analyze_feedback(feedback: Feedback):
    sentiment = TextBlob(feedback.text).sentiment.polarity
    label = "positive" if sentiment > 0 else "negative" if sentiment < 0 else "neutral"
    logging.info(
        f"/analyze: text='{feedback.text[:40]}...' | sentiment={sentiment} | label={label} | user='{feedback.user}'"
    )

    result = {"sentiment": sentiment, "label": label}

    with SessionLocal() as session:
        user = get_user(session, feedback.user) if feedback.user else None
        entry = FeedbackEntry(
            user_id=user.id if user else None,
            text=feedback.text,
            sentiment=sentiment,
            label=label,
        )
        session.add(entry)
        session.commit()

        if user:
            history_count = session.execute(
                select(func.count(FeedbackEntry.id)).where(FeedbackEntry.user_id == user.id)
            ).scalar_one()
            result["user"] = user.username
            result["historyCount"] = history_count

    return result


@app.get("/feedback/history/{username}")
def feedback_history(username: str):
    with SessionLocal() as session:
        user = get_user(session, username)
        if not user:
            return {"user": username, "entries": []}

        entries = session.execute(
            select(FeedbackEntry)
            .where(FeedbackEntry.user_id == user.id)
            .order_by(FeedbackEntry.created_at.asc())
        ).scalars().all()

        payload = [
            {
                "text": entry.text,
                "sentiment": entry.sentiment,
                "label": entry.label,
                "timestamp": entry.created_at.isoformat() + "Z",
            }
            for entry in entries
        ]

        return {"user": user.username, "entries": payload}


@app.get("/stats", response_class=HTMLResponse)
def stats_page(user: Optional[str] = None):
    with SessionLocal() as session:
        all_users = session.execute(select(User).order_by(User.username)).scalars().all()
        selected_user = get_user(session, user) if user else None

        total_feedback = 0
        avg_sentiment = None
        label_counts: List[tuple[str, int]] = []
        recent_entries: List[FeedbackEntry] = []

        if selected_user:
            total_feedback = session.execute(
                select(func.count(FeedbackEntry.id)).where(FeedbackEntry.user_id == selected_user.id)
            ).scalar_one()
            avg_sentiment = session.execute(
                select(func.avg(FeedbackEntry.sentiment)).where(FeedbackEntry.user_id == selected_user.id)
            ).scalar_one()
            label_counts = session.execute(
                select(FeedbackEntry.label, func.count(FeedbackEntry.id))
                .where(FeedbackEntry.user_id == selected_user.id)
                .group_by(FeedbackEntry.label)
            ).all()
            recent_entries = session.execute(
                select(FeedbackEntry)
                .where(FeedbackEntry.user_id == selected_user.id)
                .order_by(FeedbackEntry.created_at.desc())
                .limit(5)
            ).scalars().all()

        selected_name = selected_user.username if selected_user else (user or "")
        options_html = "".join(
            f"<option value='{escape(u.username)}' {'selected' if selected_name and selected_name.lower() == u.username.lower() else ''}>{escape(u.username)}</option>"
            for u in all_users
        )
        if not options_html:
            options_html = "<option value='' disabled>(no users yet)</option>"

        label_html = (
            "".join(
                f"<li><strong>{escape(label.title())}</strong>: {count}</li>"
                for label, count in label_counts
            )
            if label_counts
            else "<li>No feedback yet.</li>"
        )

        recent_html = (
            "".join(
                """
                <li>
                  <p>{label} • <span class='score'>{score:.3f}</span></p>
                  <p class='text'>{text}</p>
                  <time>{timestamp}</time>
                </li>
                """.format(
                    label=escape(entry.label.title()),
                    score=entry.sentiment,
                    text=escape(entry.text[:140] + ("..." if len(entry.text) > 140 else "")),
                    timestamp=entry.created_at.strftime("%Y-%m-%d %H:%M"),
                )
                for entry in recent_entries
            )
            if recent_entries
            else "<li>No recent feedback.</li>"
        )

        avg_display = f"{avg_sentiment:.3f}" if avg_sentiment is not None else "n/a"
        dominant_label = max(label_counts, key=lambda item: item[1])[0].title() if label_counts else "n/a"

        message = "" if selected_user or not user else f"User '{escape(user)}' not found."
        feedback_link = "/feedback" + (f"?user={quote(selected_name)}" if selected_user else "")

        return f"""
        <!doctype html>
        <html lang='en'>
          <head>
            <meta charset='utf-8' />
            <meta name='viewport' content='width=device-width, initial-scale=1' />
            <title>User Sentiment Stats</title>
            <style>
              * {{ box-sizing: border-box; }}
              body {{
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: #0f172a;
                color: #e2e8f0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2.5rem 1.5rem;
              }}
              .layout {{
                width: min(760px, 100%);
                display: grid;
                gap: 1.5rem;
              }}
              .card {{
                background: rgba(15, 23, 42, 0.9);
                border-radius: 18px;
                border: 1px solid rgba(148, 163, 184, 0.25);
                padding: 2rem;
                box-shadow: 0 30px 60px rgba(15, 23, 42, 0.55);
              }}
              h1 {{ margin: 0 0 1rem; font-size: 2.2rem; }}
              h2 {{ margin: 0 0 0.75rem; font-size: 1.3rem; }}
              select {{
                width: 100%;
                padding: 0.85rem 1rem;
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.35);
                background: rgba(15, 23, 42, 0.7);
                color: inherit;
                font-size: 1rem;
              }}
              select:focus {{ outline: 2px solid #38bdf8; border-color: transparent; }}
              ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 0.75rem; }}
              li {{
                background: rgba(15, 23, 42, 0.6);
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.2);
                padding: 0.85rem 1rem;
              }}
              .metrics {{ display: grid; gap: 0.75rem; margin: 1rem 0 0; }}
              .metrics span {{ font-weight: 600; }}
              .score {{ color: #38bdf8; font-weight: 600; }}
              .text {{ margin: 0.35rem 0; }}
              .nav {{ display: flex; gap: 1rem; margin-top: 1.5rem; }}
              .nav a {{ color: #38bdf8; text-decoration: none; font-weight: 600; }}
              .nav a:hover {{ text-decoration: underline; }}
              .message {{ color: #f87171; font-size: 0.95rem; margin-top: 0.75rem; }}
            </style>
          </head>
          <body>
            <div class='layout'>
              <section class='card'>
                <h1>User Sentiment Overview</h1>
                <label for='user-select'>View stats for</label>
                <select id='user-select'>
                  <option value=''>Select a user</option>
                  {options_html}
                </select>
                {f"<p class='message'>{message}</p>" if message else ""}
                <div class='nav'>
                  <a href='/login'>Back to login</a>
                  <a href='{feedback_link}'>Go to feedback</a>
                </div>
              </section>
              <section class='card'>
                <h2>Summary</h2>
                <div class='metrics'>
                  <p><span>Total feedback:</span> {total_feedback}</p>
                  <p><span>Average sentiment:</span> {avg_display}</p>
                  <p><span>Dominant tone:</span> {escape(dominant_label)}</p>
                </div>
              </section>
              <section class='card'>
                <h2>Label breakdown</h2>
                <ul>{label_html}</ul>
              </section>
              <section class='card'>
                <h2>Recent feedback</h2>
                <ul>{recent_html}</ul>
              </section>
            </div>
            <script>
              const selector = document.getElementById('user-select');
              selector.addEventListener('change', (event) => {{
                const value = event.target.value;
                const url = value ? `/stats?user=${{encodeURIComponent(value)}}` : '/stats';
                window.location.href = url;
              }});
            </script>
          </body>
        </html>
        """

# ------------------------------------------------
# AI story generation endpoint
# ------------------------------------------------
@app.post("/generate-story")
def generate_story(feedback: Feedback):
    prompt = f"Write a Jira-style user story and acceptance criteria for this feedback: {feedback.text}"

    # if no OpenAI key, return mock story
    if not openai.api_key or openai.api_key == "placeholder":
        story = f"[mock story] As a user, I want to resolve: '{feedback.text}' so that customers are happier."
        logging.info(f"/generate-story: mock story generated for text='{feedback.text[:40]}...'")
        return {"story": story}

    completion = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    story = completion.choices[0].message["content"]
    logging.info(f"/generate-story: AI story generated for text='{feedback.text[:40]}...'")
    return {"story": story}

# ------------------------------------------------
# mock insights endpoint
# ------------------------------------------------
@app.get("/insights/current")
def insights():
    logging.info("/insights/current accessed")
    return {
        "themes": [
            {"name": "Billing", "sentiment": -0.6, "count": 14},
            {"name": "Login", "sentiment": 0.4, "count": 9},
            {"name": "Performance", "sentiment": -0.1, "count": 6}
        ],
        "anomalies": ["Billing spike detected"],
        "timestamp": "2025-11-08T15:30:00Z"
    }
