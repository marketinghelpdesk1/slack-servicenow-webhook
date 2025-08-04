import os
from flask import Flask, request, jsonify
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Configuration (use environment variables or hardcoded temporarily) ---
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "xoxb-your-bot-token")
SERVICENOW_INSTANCE = os.getenv("SERVICENOW_INSTANCE", "https://dev12345.service-now.com")
SERVICENOW_USERNAME = os.getenv("SERVICENOW_USERNAME", "admin")
SERVICENOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD", "yourpassword")

# Optional: simple channel to assignment group mapping
CHANNEL_TO_ASSIGNMENT_GROUP = {
    "all-math-team": "General IT Support",
    "science-team": "Network Support",
    # Add more as needed
}


@app.route("/")
def home():
    return "Server is running!"


@app.route("/slack", methods=["POST"])
def handle_slack():
    # Extract form data from Slack
    form_data = request.form
    logging.info(f"Received Slack form data: {form_data}")

    channel_id = form_data.get("channel_id")
    channel_name = form_data.get("channel_name")
    user_name = form_data.get("user_name")
    message_text = form_data.get("text", "")
    thread_ts = form_data.get("trigger_id")  # Not actually correct for thread – updated below

    # Determine assignment group based on channel name
    assignment_group = CHANNEL_TO_ASSIGNMENT_GROUP.get(channel_name, "General IT Support")
    logging.info(f"Resolved assignment group: {assignment_group}")

    # Call ServiceNow to create incident
    servicenow_url = f"{SERVICENOW_INSTANCE}/api/now/table/incident"
    payload = {
        "short_description": f"Slack issue from {user_name}",
        "description": message_text,
        "assignment_group": assignment_group,
        "caller_id": user_name
    }

    logging.info(f"Sending request to ServiceNow: {servicenow_url} | Payload: {payload}")

    response = requests.post(
        servicenow_url,
        auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        json=payload
    )

    if response.status_code != 201:
        logging.error(f"ServiceNow error: {response.status_code} - {response.text}")
        return jsonify({"status": "failed", "error": "Failed to create ticket"}), 500

    incident_number = response.json()["result"]["number"]
    logging.info(f"Created ServiceNow incident: {incident_number}")

    # Post confirmation back to Slack in same channel/thread
    slack_payload = {
        "channel": channel_id,
        "text": f"✅ Created ServiceNow incident: *{incident_number}* for your report.",
        # You can hardcode or fetch the thread_ts based on your setup
    }

    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    slack_response = requests.post("https://slack.com/api/chat.postMessage", json=slack_payload, headers=headers)

    # --- Slack API response logging for debugging ---
    if slack_response.status_code != 200:
        logging.error(f"Slack API error: {slack_response.status_code} - {slack_response.text}")
    else:
        slack_json = slack_response.json()
        if not slack_json.get("ok"):
            logging.error(f"Slack postMessage failed: {slack_json}")
        else:
            logging.info(f"Slack message posted successfully to channel {channel_id}")

    return jsonify({"incident": incident_number, "status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
