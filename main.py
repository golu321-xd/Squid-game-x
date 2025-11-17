from flask import Flask, request, jsonify
import json
import requests
import os

app = Flask(__name__)

BOT_TOKEN = "8542259973:AAELrCAnV4et6S_RvxA-UwVTLXN2lKDTqKY"
CHAT_ID = "7704430523"

BLOCK_FILE = "blocked.json"
USER_FILE = "users.json"

def load_data(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            f.write("[]")
    with open(file, "r") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})


@app.route("/")
def home():
    return "Server is running!"


# ---------------------- TRACK ROUTE ----------------------
@app.route("/track", methods=["POST"])
def track():
    data = request.get_json()

    if not data or "username" not in data:
        return "invalid", 400

    username = data["username"]

    # Load blocked users
    blocked = load_data(BLOCK_FILE)

    # Save user in users.json
    users = load_data(USER_FILE)
    if username not in users:
        users.append(username)
        save_data(USER_FILE, users)

        # Send Telegram notification
        send_message(f"🟢 Script executed by: {username}")

    # If banned → Roblox ko batado
    if username in blocked:
        return "banned"

    return "ok"


# ---------------------- TELEGRAM BOT COMMANDS ----------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    text = data["message"].get("text", "")

    # Load blocked list
    blocked = load_data(BLOCK_FILE)

    # BAN
    if text.startswith("/ban"):
        parts = text.split()

        if len(parts) < 2:
            send_message("⚠ Username do: /ban username")
            return "ok"

        username = parts[1]
        if username not in blocked:
            blocked.append(username)
            save_data(BLOCK_FILE, blocked)

        send_message(f"🚫 {username} ko BAN kar diya gaya!")
        return "ok"

    # UNBAN
    if text.startswith("/unban"):
        parts = text.split()

        if len(parts) < 2:
            send_message("⚠ Username do: /unban username")
            return "ok"

        username = parts[1]
        if username in blocked:
            blocked.remove(username)
            save_data(BLOCK_FILE, blocked)

        send_message(f"✅ {username} ko UNBAN kar diya gaya!")
        return "ok"

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)