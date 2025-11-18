--demo video
from flask import Flask, request
import requests
import time
import json
from datetime import datetime

app = Flask(__name__)

TOKEN = "8477934891:AAE7D1WUEWWHmK8IsmNhN1hjDJgH4gAf2EA"
CHAT_ID = "6179725591"

# FILES
BLOCKED_FILE = "blocked.json"
USERS_FILE = "users.json"

# Load blocked users
def load_blocked():
    try:
        with open(BLOCKED_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

# Save blocked users
def save_blocked(data):
    with open(BLOCKED_FILE, 'w') as f:
        json.dump(data, f)

# Load executed users
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

# Save executed users
def save_users(data):
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f)

BLOCKED = load_blocked()
USERS = load_users()
WAITING = {}

# Clean expired temp bans
def cleanup_expired():
    changed = False
    for uid in list(BLOCKED.keys()):
        data = BLOCKED[uid]
        if not data.get('perm') and time.time() > data.get('expire', 0):
            del BLOCKED[uid]
            changed = True
    if changed:
        save_blocked(BLOCKED)

# Get user info (NEW API)
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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msg}, timeout=10)
    except:
        pass

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        try:
            update = request.get_json()
            if 'message' in update:
                msg = update['message']
                chat_id = str(msg['chat']['id'])
                text = msg.get('text', '').strip()

                if chat_id != CHAT_ID:
                    return "OK", 200

                # === WAITING FOR REASON ===
                if chat_id in WAITING:
                    action = WAITING[chat_id]['action']
                    user_id = WAITING[chat_id]['user_id']
                    username, display = get_user_info(user_id)

                    if action == 'add':
                        BLOCKED[user_id] = {'perm': True, 'msg': text}
                        send(f"PERM BANNED\n"
                             f"Name: {display} (@{username})\n"
                             f"ID: {user_id}\n"
                             f"Reason: {text}")
                    elif action == 'tempban':
                        mins = WAITING[chat_id].get('mins', 5)
                        expire = time.time() + (mins * 60)
                        BLOCKED[user_id] = {'perm': False, 'msg': text, 'expire': expire}
                        send(f"TEMP BANNED ({mins}m)\n"
                             f"Name: {display} (@{username})\n"
                             f"ID: {user_id}\n"
                             f"Reason: {text}")

                    del WAITING[chat_id]
                    save_blocked(BLOCKED)
                    return "OK", 200

                # === COMMANDS ===
                parts = text.split()
                cmd = parts[0]

                # /add 123
                if cmd == '/add' and len(parts) >= 2:
                    user_id = parts[1]
                    username, display = get_user_info(user_id)
                    WAITING[chat_id] = {'action': 'add', 'user_id': user_id}
                    send(f"PERM BAN\n"
                         f"Name: {display} (@{username})\n"
                         f"ID: {user_id}\n\n"
                         f"Type kick reason:")
                    return "OK", 200

                # /tempban 123 10
                elif cmd == '/tempban' and len(parts) >= 3:
                    user_id, mins = parts[1], parts[2]
                    username, display = get_user_info(user_id)
                    WAITING[chat_id] = {'action': 'tempban', 'user_id': user_id, 'mins': int(mins)}
                    send(f"TEMP BAN ({mins}m)\n"
                         f"Name: {display} (@{username})\n"
                         f"ID: {user_id}\n\n"
                         f"Type kick reason:")
                    return "OK", 200

                # /remove 123
                elif cmd == '/remove' and len(parts) >= 2:
                    user_id = parts[1]
                    username, display = get_user_info(user_id)
                    BLOCKED.pop(user_id, None)
                    save_blocked(BLOCKED)
                    send(f"UNBANNED\n"
                         f"Name: {display} (@{username})\n"
                         f"ID: {user_id}")
                    return "OK", 200

                # /list
                elif cmd == '/list':
                    cleanup_expired()
                    if not BLOCKED:
                        send("No one blocked.")
                    else:
                        res = "BLOCKED USERS:\n\n"
                        for i, (uid, data) in enumerate(BLOCKED.items(), 1):
                            username, display = get_user_info(uid)
                            t = "PERM" if data['perm'] else f"{int((data['expire'] - time.time())/60)}m left"
                            res += f"{i}. {display} (@{username})\n   ID: {uid} [{t}]\n   Reason: {data['msg']}\n\n"
                        send(res)
                    return "OK", 200

                # /clear
                elif cmd == '/clear':
                    BLOCKED.clear()
                    save_blocked(BLOCKED)
                    send("All bans cleared!")
                    return "OK", 200

                # /users - See who executed
                elif cmd == '/users':
                    if not USERS:
                        send("No users tracked yet.")
                    else:
                        res = "SCRIPT USERS:\n\n"
                        for i, (uid, info) in enumerate(USERS.items(), 1):
                            username, display = get_user_info(uid)
                            dt = datetime.fromtimestamp(info['time']).strftime("%d %b %I:%M %p")
                            res += f"{i}. {display} (@{username})\n   ID: {uid}\n   Time: {dt}\n\n"
                        send(res)
                    return "OK", 200

        except Exception as e:
            send(f"Error: {str(e)}")
    return "OK", 200

# === /check API ===
@app.route('/check/<user_id>')
def check(user_id):
    cleanup_expired()
    data = BLOCKED.get(user_id, {})
    if data.get('perm') or (not data.get('perm') and time.time() < data.get('expire', 0)):
        return "true"
    return "false"

# === /track API (called by script) ===
@app.route('/track/<user_id>/<username>/<display>')
def track(user_id, username, display):
    USERS[user_id] = {
        'username': username,
        'display': display,
        'time': time.time()
    }
    save_users(USERS)
    return "OK"

# === /reason API (CUSTOM KICK MESSAGE) ===
@app.route('/reason/<user_id>')
def get_reason(user_id):
    cleanup_expired()
    data = BLOCKED.get(user_id, {})
    if data and (data.get('perm') or time.time() < data.get('expire', 0)):
        return data.get('msg', 'Banned by Subhu Jaat')
    return ""

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
