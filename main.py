from flask import Flask, request, jsonify
import requests
import logging
from threading import Thread

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Hardcoded config (replace these)
SERVICENOW_INSTANCE = "dev351449.service-now.com"
SERVICENOW_USER = "admin"
SERVICENOW_PASSWORD = "az5CI1uA!Mm@"
SLACK_BOT_TOKEN = "xoxb-9290586945379-9317287104928-vz9WAJCypCU6OGkBHs4TO0gn"

# Channel to assignment group map
channel_to_assignment_group = {
    'math-team': 'Math Support',
    'math team': 'Math Support',
    'math room': 'Math Support',
    'science-team': 'Science Support',
    'science team': 'Science Support',
    'science room': 'Science Support',
}


@app.route("/", methods=["GET"])
def health():
    return "Server running", 200


@app.route("/slack", methods=["POST"])
def handle_slack():
    data = request.form.to_dict()
    logging.info("Received slash command: %s", data)

    # Respond immediately to avoid timeout
    Thread(target=process_request, args=(data,)).start()
    return jsonify({
        "response_type": "ephemeral",
        "text": "Creating your incident in ServiceNow..."
    }), 200


def process_request(data):
    try:
        user = data.get("user_name")
        text = data.get("text")
        channel_id = data.get("channel_id")
        channel_name = data.get("channel_name", "").lower()
        thread_ts = data.get("thread_ts") or data.get("ts")

        assignment_group = channel_to_assignment_group.get(channel_name, "General IT Support")

        # Create incident in ServiceNow
        incident_url = f"https://{SERVICENOW_INSTANCE}/api/now/table/incident"
        payload = {
            "short_description": f"Issue reported by {user} via Slack",
            "description": text,
            "assignment_group": assignment_group,
            "caller_id": user
        }

        logging.info("Creating incident in ServiceNow with payload: %s", payload)
        sn_response = requests.post(
            incident_url,
            json=payload,
            auth=(SERVICENOW_USER, SERVICENOW_PASSWORD),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )

        if sn_response.status_code == 201:
            incident = sn_response.json().get("result", {})
            incident_number = incident.get("number", "UNKNOWN")

            # Post reply in Slack thread
            slack_payload = {
                "channel": channel_id,
                "thread_ts": thread_ts,
                "text": f":white_check_mark: Incident *{incident_number}* created in ServiceNow."
            }

            slack_headers = {
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json"
            }

            logging.info("Posting back to Slack: %s", slack_payload)
            requests.post("https://slack.com/api/chat.postMessage", json=slack_payload, headers=slack_headers)
        else:
            logging.error("Failed to create incident: %s", sn_response.text)

    except Exception as e:
        logging.exception("Error processing request")


if __name__ == "__main__":
    app.run(debug=True)
