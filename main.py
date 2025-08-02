from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ENV variables (set these in Railway)
SERVICENOW_INSTANCE = os.environ.get("SERVICENOW_INSTANCE")   # e.g. dev12345.service-now.com
SERVICENOW_USER = os.environ.get("SERVICENOW_USER")
SERVICENOW_PASSWORD = os.environ.get("SERVICENOW_PASSWORD")

@app.route('/')
def index():
    return 'Flask app is running!'

@app.route('/slack', methods=['POST'])
def handle_slack_form():
    data = request.form
    user = data.get('user_name')
    text = data.get('text')
    thread_ts = data.get('thread_ts')
    channel_id = data.get('channel_id')

    # Simple fallback if thread_ts is missing
    if not thread_ts:
        thread_ts = data.get('ts', '0')

    # Map Slack channel to assignment group (customize this)
    assignment_group = {
        'math-team': 'Math Support',
        'science-team': 'Science Support'
    }.get(data.get('channel_name'), 'General IT Support')

    # Create ServiceNow incident
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
        slack_response = {
            "text": f":white_check_mark: Incident *{incident_number}* created in ServiceNow.",
            "channel": channel_id,
            "thread_ts": thread_ts
        }

        slack_url = "https://slack.com/api/chat.postMessage"
        slack_headers = {
            "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}",
            "Content-Type": "application/json"
        }

        requests.post(slack_url, json=slack_response, headers=slack_headers)
        return jsonify({"status": "ok", "incident": incident_number}), 200
    else:
        return jsonify({"error": "Failed to create incident", "details": response.text}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
