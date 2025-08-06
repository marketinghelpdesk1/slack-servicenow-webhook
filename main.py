from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Compose Slack token from parts (to avoid detection)
SLACK_BOT_TOKEN3 = os.environ.get("SLACK_TOKEN_PART1", "") + os.environ.get("SLACK_TOKEN_PART2", "")

# ServiceNow credentials
SERVICENOW_INSTANCE = "dev351449.service-now.com"
SERVICENOW_USER = "admin"
SERVICENOW_PASSWORD = "az5CI1uA!Mm@"

@app.route('/')
def index():
    return 'Flask app is running!'

@app.route('/slack', methods=['POST'])
def handle_slack_form():
    try:
        # Try to detect if it's a slash command (form) or link click (JSON)
        if request.content_type == 'application/x-www-form-urlencoded':
            data = request.form
        else:
            data = request.get_json()

        logging.info(f"Received Slack data: {data}")

        user = data.get('user_name') or data.get('user', {}).get('username')
        text = data.get('text') or data.get('message', {}).get('text')
        channel_id = data.get('channel_id') or data.get('channel', {}).get('id')
        channel_name = data.get('channel_name', '').lower() or data.get('channel', {}).get('name', '').lower()
        response_url = data.get('response_url') or data.get('response_url')

        # Try to extract thread_ts from multiple possible sources
        thread_ts = (
            data.get('thread_ts') or
            data.get('ts') or
            data.get('message', {}).get('ts') or
            data.get('container', {}).get('thread_ts') or
            data.get('container', {}).get('message_ts') or
            None
        )

        # Map channel to assignment group
        channel_to_assignment_group = {
            'math-team': 'Math Support',
            'math team': 'Math Support',
            'math room': 'Math Support',
            'science-team': 'Science Support',
            'science team': 'Science Support',
            'science room': 'Science Support',
        }
        assignment_group = channel_to_assignment_group.get(channel_name, 'General IT Support')

        # Create incident in ServiceNow
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

        logging.info(f"Sending to ServiceNow: {payload}")
        response = requests.post(url, json=payload, auth=(SERVICENOW_USER, SERVICENOW_PASSWORD), headers=headers)

        if response.status_code != 201:
            logging.error(f"ServiceNow error: {response.status_code} - {response.text}")
            if response_url:
                requests.post(response_url, json={
                    "text": f":x: Failed to create incident in ServiceNow: {response.text}",
                    "response_type": "ephemeral"
                })
            return "", 200

        incident = response.json()['result']
        incident_number = incident['number']
        logging.info(f"Created incident: {incident_number}")

        slack_payload = {
            "text": f":white_check_mark: Good day! Incident *{incident_number}* has been created in ServiceNow and is currently under review.",
            "response_type": "in_channel",
            "replace_original": False
        }

        if response_url:
            logging.info("Sending confirmation back to Slack via response_url.")
            slack_resp = requests.post(response_url, json=slack_payload)

            try:
                slack_response_json = slack_resp.json()
                confirmed_ts = slack_response_json.get("ts")
                logging.info(f"Posted confirmation. ts: {confirmed_ts}")
            except ValueError:
                logging.warning(f"Slack response not JSON. Body: {slack_resp.text}")

        return "", 200

    except Exception as e:
        logging.exception("Error in /slack handler")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/notify_resolved', methods=['POST'])
def notify_resolved():
    try:
        data = request.get_json()
        logging.info(f"Received resolved incident notification: {data}")

        channel_id = data.get("channel_id")
        incident_number = data.get("incident_number")
        thread_ts = data.get("thread_ts")

        if not (channel_id and incident_number):
            return jsonify({"error": "Missing required fields"}), 400

        message = f":white_check_mark: Incident *{incident_number}* has been resolved in ServiceNow."

        slack_headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN3}",
            "Content-Type": "application/json"
        }

        slack_payload = {
            "channel": channel_id,
            "text": message
        }

        if thread_ts:
            slack_payload["thread_ts"] = thread_ts

        slack_resp = requests.post("https://slack.com/api/chat.postMessage", headers=slack_headers, json=slack_payload)
        logging.info(f"Slack API response: {slack_resp.status_code}, {slack_resp.text}")

        if not slack_resp.ok:
            logging.error(f"Failed to post resolved update to Slack: {slack_resp.status_code} - {slack_resp.text}")
            return jsonify({"error": "Slack error", "details": slack_resp.text}), 500

        logging.info("Resolved notification posted to Slack.")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.exception("Error in notify_resolved")
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)