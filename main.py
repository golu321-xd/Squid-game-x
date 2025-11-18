from flask import Flask, request
import requests
import time
import json
import urllib.parse
from datetime import datetime

app = Flask(__name__)

TOKEN = "8535135495:AAGiAAw1Un5l-7uYkkfS-27xscYE1NU5FTE"
CHAT_ID = "7704430523"

BLOCKED_FILE = "blocked.json"
USERS_FILE = "users.json"

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
WAITING = {}

def cleanup_expired():
    changed = False
    now = time.time()
    for uid in list(BLOCKED.keys()):
        data = BLOCKED[uid]
        if not data.get("perm") and now > data.get("expire", 0):
            del BLOCKED[uid]
            changed = True
    if changed:
        save_json(BLOCKED_FILE, BLOCKED)

def get_user_info(user_id):
    try:
        url = f"https://users.roblox.com/v1/users/{user_id}"
        res = requests.get(url, timeout=5).json()
        username = res.get("name", "Unknown")
        display = res.get("displayName", username)
        return username, display
    except:
        return "Unknown", "Unknown"

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

# TELEGRAM WEBHOOK
@app.route("/", methods=["POST"])
def webhook():
    update = request.get_json()

    if not update:
        return "OK", 200

    if "message" not in update:
        return "OK", 200

    msg = update["message"]
    chat_id = str(msg["chat"]["id"])
    text = msg.get("text", "").strip()

    if chat_id != CHAT_ID:
        return "OK", 200

    # If waiting for reason
    if chat_id in WAITING:
        action = WAITING[chat_id]["action"]
        user_id = WAITING[chat_id]["user_id"]
        username, display = get_user_info(user_id)

        if action == "add":
            BLOCKED[user_id] = {"perm": True, "msg": text}
            send(f"PERM BAN\n{display} (@{username})\nID: {user_id}\nReason: {text}")

        elif action == "tempban":
            mins = WAITING[chat_id]["mins"]
            expire = time.time() + mins * 60
            BLOCKED[user_id] = {"perm": False, "msg": text, "expire": expire}
            send(f"TEMP BAN ({mins}m)\n{display} (@{username})\nID: {user_id}\nReason: {text}")

        save_json(BLOCKED_FILE, BLOCKED)
        del WAITING[chat_id]
        return "OK", 200

    parts = text.split()
    cmd = parts[0]

    # /add 123
    if cmd == "/add" and len(parts) >= 2:
        uid = parts[1]
        username, display = get_user_info(uid)
        WAITING[chat_id] = {"action": "add", "user_id": uid}
        send(f"PERM BAN\n{display} (@{username})\nID: {uid}\n\nType reason:")
        return "OK"

    # /tempban 123 10
    if cmd == "/tempban" and len(parts) >= 3:
        uid, mins = parts[1], int(parts[2])
        username, display = get_user_info(uid)
        WAITING[chat_id] = {"action": "tempban", "user_id": uid, "mins": mins}
        send(f"TEMP BAN ({mins}m)\n{display} (@{username})\nID: {uid}\n\nType reason:")
        return "OK"

    # /remove 123
    if cmd == "/remove" and len(parts) >= 2:
        uid = parts[1]
        BLOCKED.pop(uid, None)
        save_json(BLOCKED_FILE, BLOCKED)
        send(f"UNBANNED {uid}")
        return "OK"

    # /list
    if cmd == "/list":
        cleanup_expired()
        if not BLOCKED:
            send("No banned users.")
        else:
            msg = "BLOCKED USERS:\n\n"
            for uid, data in BLOCKED.items():
                username, display = get_user_info(uid)
                if data["perm"]:
                    status = "PERM"
                else:
                    left = int((data["expire"] - time.time()) / 60)
                    status = f"{left}m left"
                msg += f"{display} (@{username}) - {uid} [{status}]\nReason: {data['msg']}\n\n"
            send(msg)
        return "OK"

    return "OK"

# /check API
@app.route("/check/<uid>")
def check(uid):
    cleanup_expired()
    data = BLOCKED.get(uid, None)
    if not data:
        return "false"
    if data["perm"]:
        return "true"
    if time.time() < data["expire"]:
        return "true"
    return "false"

# /track API
@app.route("/track/<uid>/<username>/<display>")
def track(uid, username, display):
    username = urllib.parse.unquote(username)
    display = urllib.parse.unquote(display)

    USERS[uid] = {"username": username, "display": display, "time": time.time()}
    save_json(USERS_FILE, USERS)
    return "OK"

# /reason
@app.route("/reason/<uid>")
def reason(uid):
    cleanup_expired()
    data = BLOCKED.get(uid, None)
    if not data:
        return ""
    return data.get("msg", "Banned by Subhu Jaat")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)