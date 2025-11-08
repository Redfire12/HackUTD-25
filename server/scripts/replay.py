import json
import time
import requests
from datetime import datetime, timezone

BACKEND_URL = "http://127.0.0.1:8000/ingest"

def load_feedback(file_path="sample_feedback.json"):
    with open(file_path, "r") as f:
        return json.load(f)

def stream_feedback(feedback_list, delay=3):
    for item in feedback_list:
        item["timestamp"] = datetime.now(timezone.utc).isoformat()
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
    stream_feedback(feedback_data, delay=3)
