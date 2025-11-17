from flask import Flask, request
import requests
import time
import json
from datetime import datetime

app = Flask(__name__)

# ==========================
# CONFIG
# ==========================

TOKEN = "8535135495:AAGiAAw1Un5l-7uYkkfS-27xscYE1NU5FTE"
CHAT_ID = "7704430523"

BLOCKED_FILE = "blocked.json"
USERS_FILE = "users.json"

# ==========================
# FILE LOADING / SAVING
# ==========================

def load_blocked():
    try:
        with open(BLOCKED_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_blocked(data):
    with open(BLOCKED_FILE, 'w') as f:
        json.dump(data, f)

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f)

BLOCKED = load_blocked()
USERS = load_users()
WAITING = {}

# ==========================
# HELPERS
# ==========================

def cleanup_expired():
    changed = False
    for uid in list(BLOCKED.keys()):
        data = BLOCKED[uid]
        if not data.get("perm") and time.time() > data.get("expire", 0):
            del BLOCKED[uid]
            changed = True
    if changed:
        save_blocked(BLOCKED)

def get_user_info(user_id):
    try:
        url = f"https://users.roblox.com/v1/users/{user_id}"
        data = requests.get(url, timeout=5).json()
        username = data.get("name", "Unknown")
        display = data.get("displayName", username)
        return username, display
    except:
        return "Unknown", "Unknown"

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msg}, timeout=10)
    except:
        pass

# ==========================
# TELEGRAM WEBHOOK
# ==========================

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        try:
            update = request.get_json()
            if not update or "message" not in update:
                return "OK", 200

            msg = update["message"]
            chat_id = str(msg["chat"]["id"])
            text = msg.get("text", "").strip()

            if chat_id != CHAT_ID:
                return "OK", 200

            # ==========================
            # WAITING for REASON
            # ==========================
            if chat_id in WAITING:
                action = WAITING[chat_id]["action"]
                user_id = WAITING[chat_id]["user_id"]
                username, display = get_user_info(user_id)

                if action == "add":
                    BLOCKED[user_id] = {"perm": True, "msg": text}
                    send(f"PERM BANNED\nName: {display} (@{username})\nID: {user_id}\nReason: {text}")

                elif action == "tempban":
                    mins = WAITING[chat_id]["mins"]
                    expire = time.time() + mins * 60
                    BLOCKED[user_id] = {"perm": False, "msg": text, "expire": expire}
                    send(f"TEMP BANNED ({mins}m)\nName: {display} (@{username})\nID: {user_id}\nReason: {text}")

                save_blocked(BLOCKED)
                del WAITING[chat_id]
                return "OK", 200

            # ==========================
            # COMMANDS
            # ==========================
            parts = text.split()
            cmd = parts[0]

            # /add 123
            if cmd == "/add" and len(parts) >= 2:
                user_id = parts[1]
                username, display = get_user_info(user_id)
                WAITING[chat_id] = {"action": "add", "user_id": user_id}
                send(f"PERM BAN\nName: {display} (@{username})\nID: {user_id}\n\nType kick reason:")
                return "OK", 200

            # /tempban 123 10
            elif cmd == "/tempban" and len(parts) >= 3:
                user_id = parts[1]
                mins = int(parts[2])
                username, display = get_user_info(user_id)
                WAITING[chat_id] = {"action": "tempban", "user_id": user_id, "mins": mins}
                send(f"TEMP BAN ({mins}m)\nName: {display} (@{username})\nID: {user_id}\n\nType kick reason:")
                return "OK", 200

            # /remove 123
            elif cmd == "/remove" and len(parts) >= 2:
                user_id = parts[1]
                BLOCKED.pop(user_id, None)
                save_blocked(BLOCKED)
                username, display = get_user_info(user_id)
                send(f"UNBANNED\nName: {display} (@{username})\nID: {user_id}")
                return "OK", 200

            # /list
            elif cmd == "/list":
                cleanup_expired()
                if not BLOCKED:
                    send("No one blocked.")
                else:
                    res = "BLOCKED USERS:\n\n"
                    for i, (uid, data) in enumerate(BLOCKED.items(), 1):
                        username, display = get_user_info(uid)
                        t = "PERM" if data["perm"] else f"{int((data['expire'] - time.time())/60)}m left"
                        res += f"{i}. {display} (@{username})\nID: {uid} [{t}]\nReason: {data['msg']}\n\n"
                    send(res)
                return "OK", 200

            # /users
            elif cmd == "/users":
                if not USERS:
                    send("No users tracked yet.")
                else:
                    res = "SCRIPT USERS:\n\n"
                    for i, (uid, info) in enumerate(USERS.items(), 1):
                        username, display = get_user_info(uid)
                        dt = datetime.fromtimestamp(info["time"]).strftime("%d %b %I:%M %p")
                        res += f"{i}. {display} (@{username})\nID: {uid}\nTime: {dt}\n\n"
                    send(res)
                return "OK", 200

            # /clear
            elif cmd == "/clear":
                BLOCKED.clear()
                save_blocked(BLOCKED)
                send("All bans cleared!")
                return "OK", 200

        except Exception as e:
            send("Error: " + str(e))

    return "OK", 200

# ==========================
# CHECK API
# ==========================

@app.route("/check/<user_id>")
def check(user_id):
    cleanup_expired()
    data = BLOCKED.get(user_id, {})
    if data.get("perm") or (not data.get("perm") and time.time() < data.get("expire", 0)):
        return "true"
    return "false"

# ==========================
# TRACK API (BEST VERSION)
# Roblox only sends user_id
# ==========================

@app.route("/track/<user_id>")
def track(user_id):
    username, display = get_user_info(user_id)
    USERS[user_id] = {
        "username": username,
        "display": display,
        "time": time.time()
    }
    save_users(USERS)
    return "OK"

# ==========================
# CUSTOM BAN MESSAGE API
# ==========================

@app.route("/reason/<user_id>")
def reason(user_id):
    cleanup_expired()
    data = BLOCKED.get(user_id, {})
    if data and (data.get("perm") or time.time() < data.get("expire", 0)):
        return data.get("msg", "Banned by Saksham")
    return ""

# ==========================
# TEST API (for reqbin)
# ==========================

@app.route("/test", methods=["POST"])
def test():
    data = request.get_json()
    if not data:
        return {"error": "No JSON"}, 400

    username = data.get("username", "Unknown User")
    action = data.get("action", "script-executed")

    send(f"TEST OK ✅\nUser: {username}\nAction: {action}")

    return {"status": "ok"}, 200

# ==========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)