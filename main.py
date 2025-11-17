from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

BOT_TOKEN = "8542259973:AAELrCAnV4et6S_RvxA-UwVTLXN2lKDTqKY"
CHAT_ID = "7704430523"

ban_list = set()

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=data)


@app.route("/", methods=["GET"])
def home():
    return "Server is running!"


# ------------------- TRACK ROUTE FOR ROBLOX -------------------
@app.route("/track", methods=["POST"])
def track():
    data = request.get_json()

    if not data or "username" not in data:
        return "invalid", 400

    username = data["username"]

    if username in ban_list:
        return "banned"
    else:
        return "ok"


# ------------------- TELEGRAM WEBHOOK -------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    chat = data["message"]
    text = chat.get("text", "")

    # BAN command
    if text.startswith("/ban"):
        parts = text.split()

        if len(parts) < 2:
            send_message("⚠ Username dena bhai: /ban username")
            return "ok"

        username = parts[1]
        ban_list.add(username)
        send_message(f"🚫 '{username}' ko BAN kar diya gaya!")
        return "ok"

    # UNBAN command
    if text.startswith("/unban"):
        parts = text.split()

        if len(parts) < 2:
            send_message("⚠ Username dena bhai: /unban username")
            return "ok"

        username = parts[1]
        ban_list.discard(username)
        send_message(f"✅ '{username}' ko UNBAN kar diya gaya!")
        return "ok"

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)