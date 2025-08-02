from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ServiceNow and Slack environment variables
SERVICENOW_INSTANCE = os.environ.get("SERVICENOW_INSTANCE")  # e.g., 'dev12345'
SERVICENOW_USERNAME = os.environ.get("SERVICENOW_USERNAME")
SERVICENOW_PASSWORD = os.environ.get("SERVICENOW_PASSWORD")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")  # xoxb-xxx
HEADERS = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}

@app.route("/", methods=["GET"])
def healthcheck():
    return "Flask app is running!"

@app.route("/slack", methods=["POST"])
def handle_slack():
    data = request.form
    user = data.get("user_name")
    text = data.get("text")
    channel_id = data.get("channel_id")
    response_url = data.get("response_url")

    # Create ServiceNow ticket
    sn_url = f"https://{SERVICENOW_INSTANCE}.service-now.com/api/now/table/incident"
    payload = {
        "short_description": f"Issue from {user}: {text}",
        "description": f"Slack user {user} reported: {text}",
        "assignment_group": "Hardware",  # Or change this as needed
        "caller_id": user
    }

    response = requests.post(
        sn_url,
        auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 201:
        incident_number = response.json()["result"]["number"]
        reply = f":white_check_mark: Created ServiceNow ticket *{incident_number}* for your issue."
    else:
        reply = f":x: Failed to create ServiceNow ticket. Error: {response.text}"

    # Post reply to Slack
    slack_response = {
        "response_type": "in_channel",
        "text": reply
    }
    requests.post(response_url, json=slack_response)

    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
