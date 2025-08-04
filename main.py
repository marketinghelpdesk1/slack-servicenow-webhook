from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Enable basic logging
logging.basicConfig(level=logging.INFO)

# Root route for test/debug in browser
@app.route('/', methods=['GET'])
def index():
    return 'Slack Flask app is running!'

# Slack Slash Command handler
@app.route('/slack', methods=['POST'])
def slack_handler():
    data = request.form
    logging.info("Received Slack data: %s", data)

    user_id = data.get('user_id')
    command = data.get('command')
    text = data.get('text')
    response_url = data.get('response_url')
    channel_id = data.get('channel_id')

    # Optional: you can route this to ServiceNow or logic here
    message = f":ticket: <@{user_id}> reported an issue:\n{text}"

    return jsonify({
        "response_type": "in_channel",  # "ephemeral" makes it visible only to the user
        "text": message
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
