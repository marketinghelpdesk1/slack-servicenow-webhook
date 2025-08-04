from flask import Flask, request, jsonify
import json
import requests
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# Update these as needed
SERVICENOW_URL = "dev351449.service-now.com/api/now/table/incident"
SERVICENOW_USER = "admin"
SERVICENOW_PASSWORD = "az5CI1uA!Mm@"

CHANNEL_TO_ASSIGNMENT_GROUP = {
    "math-team": "Math Support",
    "science-team": "Science Support"
}

@app.route("/", methods=["GET"])
def index():
    return "Slack to ServiceNow webhook is running."

@app.route("/slack", methods=["POST"])
def slack_handler():
    payload = request.form

    logging.info("Received form: %s", payload)

    text = payload.get("text", "")
    user_id = payload.get("user_id")
    channel_name = payload.get("channel_name")
    response_url = payload.get("response_url")
    thread_ts = payload.get("thread_ts") or payload.get("ts")  # fallback if thread_ts is missing

    # Determine assignment group
    assignment_group = CHANNEL_TO_ASSIGNMENT_GROUP.get(channel_name, "Default Support")

    # Create incident in ServiceNow
    incident_data = {
        "short_description": f"Issue from {channel_name} via Slack",
        "description": f"{text}\nReported by Slack user <@{user_id}>",
        "assignment_group": assignment_group,
        "caller_id": "Slack Integration",
        "category": "Inquiry / Help"
    }

    logging.info("Sending incident to ServiceNow: %s", incident_data)

    response = requests.post(
        SERVICENOW_URL,
        auth=(SERVICENOW_USER, SERVICENOW_PASSWORD),
        headers={"Content-Type": "application/json"},
        data=json.dumps(incident_data)
    )

    if response.status_code in [200, 201]:
        incident = response.json().get("result", {})
        number = incident.get("number", "INCXXXX")
        message = f":white_check_mark: Incident *{number}* created and assigned to *{assignment_group}*."
    else:
        logging.error("Failed to create incident: %s", response.text)
        message = f":x: Failed to create ServiceNow ticket. Error: {response.status_code}"

    # Post back to Slack via response_url
    slack_reply = {
        "response_type": "in_channel",
        "text": message
    }

    logging.info("Posting back to Slack: %s", slack_reply)

    requests.post(response_url, json=slack_reply)

    return "", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
