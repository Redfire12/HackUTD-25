# backend/database.py
import sqlite3

conn = sqlite3.connect("data/feedback.db", check_same_thread=False)
c = conn.cursor()

# Create table if not exists
c.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    timestamp TEXT,
    source TEXT,
    sentiment TEXT,
    theme TEXT
)
""")
conn.commit()

def insert_feedback(feedback):
    c.execute("""
    INSERT INTO feedback (text, timestamp, source, sentiment, theme)
    VALUES (?, ?, ?, ?, ?)
    """, (feedback["text"], feedback["timestamp"], feedback["source"], feedback["sentiment"], feedback["theme"]))
    conn.commit()

def get_all_feedback():
    c.execute("SELECT * FROM feedback")
    return c.fetchall()
