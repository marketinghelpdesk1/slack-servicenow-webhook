from threading import Thread

@app.route('/slack', methods=['POST'])
def handle_slack_form():
    data = request.form
    logging.info(f"Received Slack form data: {data}")

    # Immediate response to Slack
    Thread(target=process_slack_request, args=(data,)).start()
    return '', 200

def process_slack_request(data):
    try:
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
        logging.info(f"Resolved assignment group: {assignment_group}")

        # ServiceNow API call
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
            return

        incident = response.json()['result']
        incident_number = incident['number']
        logging.info(f"Created ServiceNow incident: {incident_number}")

        # Post back to Slack thread
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
        if not slack_resp.ok:
            logging.error(f"Failed to post to Slack: {slack_resp.status_code} - {slack_resp.text}")
        else:
            logging.info("Posted confirmation to Slack.")

    except Exception as e:
        logging.exception("Error processing Slack request.")
