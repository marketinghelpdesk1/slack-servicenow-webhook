from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Hardcoded for now
SERVICENOW_INSTANCE = "dev351449.service-now.com"
SERVICENOW_USER = "admin"
SERVICENOW_PASSWORD = "az5CI1uA!Mm@"
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "xoxb-YOUR-SLACK-TOKEN")

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
        thread_ts = data.get('thread_ts') or data.get('ts') or None
        channel_id = data.get('channel_id')
        channel_name = data.get('channel_name', '').lower()

        # Map channel name to assignment group
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

        # Create incident in ServiceNow
        url = f"https://{SERVICENOW_INSTANCE}/api/now/table/incident"
        payload = {
            "short_description": f"Slack issue from {user}",
            "description": text,
            "assignment_group": assignment_group,
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
            return jsonify({"error": "Failed to create incident", "details": response.text}), 500

        incident = response.json()['result']
        incident_number = incident['number']
        logging.info(f"Created ServiceNow incident: {incident_number}")

        # ✅ Post message to Slack (in thread)
        slack_url = "https://slack.com/api/chat.postMessage"
        slack_headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        slack_payload = {
            "channel": channel_id,
            "text": f":white_check_mark: ServiceNow ticket *{incident_number}* created successfully.",
        }

        # If original message had thread_ts, reply in thread
        if thread_ts:
            slack_payload["thread_ts"] = thread_ts

        slack_resp = requests.post(slack_url, json=slack_payload, headers=slack_headers)
        if not slack_resp.ok:
            logging.error(f"Failed to post to Slack: {slack_resp.status_code} - {slack_resp.text}")
        else:
            logging.info("Posted confirmation to Slack thread.")

        # ✅ Respond quickly to Slack (only user sees this)
        return jsonify(
            {
                "response_type": "ephemeral",
                "text": f"Creating your ServiceNow ticket... (Incident: {incident_number})"
            }
        ), 200

    except Exception as e:
        logging.exception("Unhandled error during Slack request")
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
