from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ENV variables (set these in Railway or your environment)
SERVICENOW_INSTANCE = os.environ.get("SERVICENOW_INSTANCE")   # e.g. dev12345.service-now.com
SERVICENOW_USER = os.environ.get("SERVICENOW_USER")
SERVICENOW_PASSWORD = os.environ.get("SERVICENOW_PASSWORD")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

@app.route('/')
def index():
    return 'Flask app is running!'

@app.route('/slack', methods=['POST'])
def handle_slack_form():
    data = request.form
    user = data.get('user_name')
    text = data.get('text')
    thread_ts = data.get('thread_ts') or data.get('ts')
    channel_id = data.get('channel_id')
    channel_name = data.get('channel_name', '').lower()

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

    # Prepare ServiceNow payload
    url = f"https://{SERVICENOW_INSTANCE}/api/now/table/incident"
    payload = {
        "short_description": f"Slack issue from {user}",
        "description": text,
        "assignment_group": assignment_group,
        "caller_id": user
    }

    response = requests.post(url, json=payload, auth=(SERVICENOW_USER, SERVICENOW_PASSWORD), headers={
        "Content-Type": "application/json",
        "Accept": "application/json"
    })

    if response.status_code == 201:
        incident = response.json()['result']
        incident_number = incident['number']

        # Send reply to Slack thread
        slack_url = "https://slack.com/api/chat.postMessage"
        slack_headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        slack_payload = {
            "channel": channel_id,
            "thread_ts": thread_ts,
            "text": f":white_check_mark: Incident *{incident_number}* created in ServiceNow."
        }

        slack_resp = requests.post(slack_url, json=slack_payload, headers=slack_headers)
        return jsonify({"status": "ok", "incident": incident_number}), 200
    else:
        return jsonify({"error": "Failed to create incident", "details": response.text}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
