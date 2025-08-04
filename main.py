from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Hardcoded for testing; replace with os.environ.get(...) in production
SERVICENOW_INSTANCE = "dev351449.service-now.com"
SERVICENOW_USER = "admin"
SERVICENOW_PASSWORD = "az5CI1uA!Mm@"
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "xoxb-9290586945379-9317287104928-CXa3TNqNtnFujcYt5GT7B4pC")

@app.route('/')
def index():
    return 'Flask app is running!'

@app.route('/slack', methods=['POST'])
def handle_slack_form():
    try:
        data = request.form
        logging.info(f"Received Slack form data: {data}")

        user = data.get('user_name')
        text = data.get('text')
        channel_id = data.get('channel_id')
        channel_name = data.get('channel_name', '').lower()
        response_url = data.get('response_url')
        thread_ts = data.get('thread_ts') or data.get('trigger_id') or None

        # Map Slack channel name to assignment group
        channel_to_assignment_group = {
            'math-team': 'Math Support',
            'math team': 'Math Support',
            'math room': 'Math Support',
            'science-team': 'Science Support',
            'science team': 'Science Support',
            'science room': 'Science Support',
        }

        assignment_group = channel_to_assignment_group.get(channel_name, 'General IT Support')
        logging.info(f"Resolved assignment group: {assignment_group}")

        # Prepare ServiceNow payload
        url = f"https://{SERVICENOW_INSTANCE}/api/now/table/incident"
        payload = {
            "short_description": f"Slack issue from {user}",
            "description": text,
            "assignment_group": assignment_group,
            "u_slack_channel_id": channel_id,
            "u_slack_thread_ts": thread_ts,
            "caller_id": user
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        logging.info(f"Sending request to ServiceNow: {url} | Payload: {payload}")
        response = requests.post(url, json=payload, auth=(SERVICENOW_USER, SERVICENOW_PASSWORD), headers=headers)

        if response.status_code != 201:
            logging.error(f"ServiceNow error: {response.status_code} - {response.text}")
            requests.post(response_url, json={
                "text": f":x: Failed to create incident in ServiceNow: {response.text}",
                "response_type": "ephemeral"
            })
            return "", 200

        incident = response.json()['result']
        incident_number = incident['number']
        logging.info(f"Created ServiceNow incident: {incident_number}")

        # Post to the channel using response_url
        slack_payload = {
            "text": f":white_check_mark: Good day! Incident *{incident_number}* has been created in ServiceNow and is currently under review. We'll update you soon. Thank you.",
            "response_type": "in_channel",  # This makes the message visible to everyone
            "replace_original": False
        }

        logging.info("Sending confirmation to Slack channel via response_url.")
        slack_resp = requests.post(response_url, json=slack_payload)
        if not slack_resp.ok:
            logging.error(f"Failed to post to Slack: {slack_resp.status_code} - {slack_resp.text}")
        else:
            logging.info("Posted confirmation to Slack.")

        return "", 200

    except Exception as e:
        logging.exception("Unhandled error during Slack request")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/notify_resolved', methods=['POST'])
def notify_resolved():
    data = request.get_json()
    logging.info(f"Received resolved incident notification: {data}")

    channel_id = data.get("channel_id")
    thread_ts = data.get("thread_ts")
    incident_number = data.get("incident_number")

    if not (channel_id and thread_ts and incident_number):
        return jsonify({"error": "Missing required fields"}), 400

    message = f":white_check_mark: Incident *{incident_number}* has been resolved in ServiceNow."

    slack_headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    slack_payload = {
        "channel": channel_id,
    #    "thread_ts": thread_ts,
        "text": message
    }

    slack_resp = requests.post("https://slack.com/api/chat.postMessage", json=slack_payload, headers=slack_headers)
    
    if not slack_resp.ok:
        logging.error(f"Failed to post resolved update to Slack: {slack_resp.status_code} - {slack_resp.text}")
        return jsonify({"error": "Slack error", "details": slack_resp.text}), 500

    logging.info("Resolved incident notification posted to Slack.")
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)





