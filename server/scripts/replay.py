import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import time
import requests
from datetime import datetime, timezone
import re

def redact_pii(text: str) -> str:
    """
    Redact emails and phone numbers from text.
    """
    # Remove emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', "[REDACTED_EMAIL]", text)
    
    # Remove phone numbers (simple patterns)
    text = re.sub(r'\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b', "[REDACTED_PHONE]", text)
    
    return text

# -------------------------------
# TF-IDF + KMeans Clustering
# -------------------------------
def cluster_feedback(feedback_texts, n_clusters=3):
    vectorizer = TfidfVectorizer(stop_words='english')
    X = vectorizer.fit_transform(feedback_texts)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(X)
    return kmeans.labels_

BACKEND_URL = "http://127.0.0.1:8000/ingest"

def load_feedback(file_path="sample_feedback.json"):
    with open(file_path, "r") as f:
        return json.load(f)

def stream_feedback(feedback_list, delay=3, n_clusters=3):
    # First, extract all texts for clustering
    feedback_texts = [redact_pii(item["text"]) for item in feedback_list]
    labels = cluster_feedback(feedback_texts, n_clusters=n_clusters)

    for i, item in enumerate(feedback_list):
        item["timestamp"] = datetime.now(timezone.utc).isoformat()
        item["text"] = redact_pii(item["text"])
        item["theme"] = f"Theme {labels[i]+1}"

        try:
            response = requests.post(BACKEND_URL, json=item)
            if response.status_code == 200:
                print(f"✅ Sent: {item['text'][:60]}...")
            else:
                print(f"⚠️ Failed ({response.status_code}): {item['text'][:60]}...")
        except Exception as e:
            print(f"❌ Error sending feedback: {e}")
        time.sleep(delay)

if __name__ == "__main__":
    feedback_data = load_feedback()
    print(f"📡 Starting replay of {len(feedback_data)} feedback items...")
    stream_feedback(feedback_data, delay=3, n_clusters=3)
