from flask import Flask, request, jsonify
import json
import time
import requests

app = Flask(__name__)

TOKEN = "8535135495:AAGiAAw1Un5l-7uYkkfS-27xscYE1NU5FTE"
CHAT_ID = "7704430523"

BLOCKED_FILE = "blocked.json"

def load_blocked():
    try:
        with open(BLOCKED_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_blocked(data):
    with open(BLOCKED_FILE, "w") as f:
        json.dump(data, f)

BLOCKED = load_blocked()

def send_to_telegram(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    requests.post(url, data=payload)

# =============== TRACK API (called by Roblox script) ===============
@app.route("/track", methods=["POST"])
def track_user():
    data = request.json
    username = data.get("username")

    if not username:
        return "invalid", 400

    # Check ban status
    if username in BLOCKED:
        return "banned"

    # Send message with Ban/Unban buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🚫 Ban", "callback_data": f"ban:{username}"},
                {"text": "✅ Unban", "callback_data": f"unban:{username}"}
            ]
        ]
    }

    send_to_telegram(f"User Executed Script:\n👤 <b>{username}</b>", keyboard)

    return "ok"

# =============== TELEGRAM CALLBACKS ===============
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.json

    if "callback_query" not in data:
        return "ok"

    q = data["callback_query"]
    chat_id = q["message"]["chat"]["id"]

    if str(chat_id) != CHAT_ID:
        return "ok"

    action, username = q["data"].split(":")

    if action == "ban":
        BLOCKED[username] = True
        save_blocked(BLOCKED)
        send_to_telegram(f"🚫 <b>{username}</b> has been <b>BANNED</b>")

    elif action == "unban":
        BLOCKED.pop(username, None)
        save_blocked(BLOCKED)
        send_to_telegram(f"✅ <b>{username}</b> is now <b>UNBANNED</b>")

    return "ok"

@app.route("/")
def home():
    return "Server Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)