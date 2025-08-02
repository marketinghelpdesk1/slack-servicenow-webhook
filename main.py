from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SN_INSTANCE = os.getenv("SN_INSTANCE")
SN_USER = os.getenv("SN_USER")
SN_PASS = os.getenv("SN_PASS")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    text = data.get("text", "")
    user = data.get("user", "")
    channel = data.get("channel")
    thread_ts = data.get("thread_ts")

    # Step 1: Create incident in ServiceNow
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "short_description": f"Issue from Slack user {user}",
        "description": text,
        "caller_id": user
    }

    response = requests.post(
        f"{SN_INSTANCE}/api/now/table/incident",
        auth=(SN_USER, SN_PASS),
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        number = response.json()["result"]["number"]
        reply_text = f"✅ Incident created: *{number}*"
    else:
        reply_text = f"⚠️ Failed to create incident. Status: {response.status_code}"

    # Step 2: Reply back in Slack
    slack_response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "channel": channel,
            "text": reply_text,
            "thread_ts": thread_ts
        }
    )

    return jsonify({"message": "Processed"}), 200
