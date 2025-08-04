from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/slack', methods=['POST'])
def slack_command():
    data = request.form
    user = data.get('user_name')
    channel_id = data.get('channel_id')
    text = data.get('text')

    # Response to slash command (only visible to user)
    response_text = f"Thanks {user}, we're processing your issue: '{text}'. A ticket will be created shortly."

    return jsonify({
        "response_type": "ephemeral",  # use "in_channel" to make it visible to everyone
        "text": response_text
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
