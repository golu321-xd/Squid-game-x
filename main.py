from flask import Flask, request
import requests
import json
import time
from datetime import datetime

app = Flask(__name__)

# ==========================
# CONFIG (YOUR DETAILS ADDED)
# ==========================
TOKEN = "8516360209:AAHixZSpWCsl8HMyTayVHvinBa7pNS1dR68"
CHAT_ID = "7704430523"

BASE = f"https://api.telegram.org/bot{TOKEN}"
SENDMSG = BASE + "/sendMessage"

BLOCKED_FILE = "blocked.json"
USERS_FILE = "users.json"


# ==========================
# FILE LOAD / SAVE
# ==========================
def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

BLOCKED = load_json(BLOCKED_FILE)
USERS = load_json(USERS_FILE)


# ==========================
# UTIL FUNCTIONS
# ==========================
def send(msg, reply_markup=None):
    data = {"chat_id": CHAT_ID, "text": msg}

    if reply_markup:
        data["reply_markup"] = reply_markup

    try:
        requests.post(SENDMSG, json=data)
    except:
        pass


def get_user_info(user_id):
    try:
        url = f"https://users.roblox.com/v1/users/{user_id}"
        data = requests.get(url).json()
        username = data.get("name", "Unknown")
        display = data.get("displayName", username)
        return username, display
    except:
        return "Unknown", "Unknown"


# ==========================
# CLEAN EXPIRED TEMP BANS
# ==========================
def cleanup():
    changed = False
    for uid in list(BLOCKED.keys()):
        data = BLOCKED[uid]
        if not data.get("perm") and time.time() > data.get("expire", 0):
            del BLOCKED[uid]
            changed = True
    if changed:
        save_json(BLOCKED_FILE, BLOCKED)


# ==========================
# TELEGRAM WEBHOOK
# ==========================
@app.route("/", methods=["POST", "GET"])
def webhook():
    if request.method == "POST":
        update = request.get_json()

        # ====== BUTTON PRESS ======
        if "callback_query" in update:
            cb = update["callback_query"]
            data = cb["data"]

            # BAN
            if data.startswith("ban_"):
                user_id = data.replace("ban_", "")
                username, display = get_user_info(user_id)

                BLOCKED[user_id] = {
                    "perm": True,
                    "msg": "Banned by Saksham"
                }
                save_json(BLOCKED_FILE, BLOCKED)

                send(f"🚫 PERM BANNED\nName: {display}\nID: {user_id}")

            # UNBAN
            elif data.startswith("unban_"):
                user_id = data.replace("unban_", "")
                username, display = get_user_info(user_id)

                BLOCKED.pop(user_id, None)
                save_json(BLOCKED_FILE, BLOCKED)

                send(f"♻️ UNBANNED\nName: {display}\nID: {user_id}")

            return "OK", 200


        # ====== MANUAL COMMANDS ======
        if "message" in update:
            msg = update["message"]
            text = msg.get("text", "")

            if str(msg["chat"]["id"]) != CHAT_ID:
                return "OK", 200

            parts = text.split()
            cmd = parts[0]

            if cmd == "/list":
                cleanup()
                if not BLOCKED:
                    send("No blocked users.")
                else:
                    res = "🚫 BLOCKED USERS:\n\n"
                    for uid, data in BLOCKED.items():
                        username, display = get_user_info(uid)
                        res += f"{display} (@{username})\nID: {uid}\nReason: {data['msg']}\n\n"
                    send(res)

            elif cmd == "/users":
                if not USERS:
                    send("No users tracked yet.")
                else:
                    res = "⚡ SCRIPT USERS:\n\n"
                    for uid, info in USERS.items():
                        username, display = get_user_info(uid)
                        ts = datetime.fromtimestamp(info["time"]).strftime("%d %b %I:%M %p")
                        res += f"{display} (@{username})\nID: {uid}\nTime: {ts}\n\n"
                    send(res)

    return "OK", 200


# ==========================
# API FOR ROBLOX
# ==========================

@app.route("/track/<user_id>/<username>/<display>")
def track(user_id, username, display):

    USERS[user_id] = {
        "username": username,
        "display": display,
        "time": time.time()
    }
    save_json(USERS_FILE, USERS)

    send(
        f"⚡ SCRIPT EXECUTED\nName: {display}\nID: {user_id}",
        reply_markup={
            "inline_keyboard": [
                [
                    {"text": "🚫 Ban", "callback_data": f"ban_{user_id}"},
                    {"text": "♻️ Unban", "callback_data": f"unban_{user_id}"}
                ]
            ]
        }
    )

    return "OK"


@app.route("/check/<user_id>")
def check(user_id):
    cleanup()
    if user_id in BLOCKED:
        return "true"
    return "false"


@app.route("/reason/<user_id>")
def reason(user_id):
    cleanup()
    if user_id in BLOCKED:
        return BLOCKED[user_id]["msg"]
    return ""


# ==========================
# RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)