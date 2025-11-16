from flask import Flask, request
import requests
import time
import json
from datetime import datetime

app = Flask(__name__)

# === CONFIG ===
TOKEN = "8516360209:AAHixZSpWCsl8HMyTayVHvinBa7pNS1dR68"
CHAT_ID = "7704430523"

# FILES
BLOCKED_FILE = "blocked.json"
USERS_FILE = "users.json"

# === Helper Functions ===

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

# Clean expired temporary bans
def cleanup_expired():
    changed = False
    for uid in list(BLOCKED.keys()):
        data = BLOCKED[uid]
        if not data.get('perm') and time.time() > data.get('expire', 0):
            del BLOCKED[uid]
            changed = True
    if changed:
        save_blocked(BLOCKED)

# Get Roblox user info
def get_user_info(user_id):
    try:
        url = f"https://users.roblox.com/v1/users/{user_id}"
        data = requests.get(url, timeout=5).json()
        username = data.get("name", "Unknown")
        display = data.get("displayName", username)
        return username, display
    except:
        return "Unknown", "Unknown"

# Telegram send with optional inline buttons
def send(msg, buttons=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
    if buttons:
        data['reply_markup'] = json.dumps({'inline_keyboard': buttons})
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code != 200:
            print("Telegram API Error:", r.text)
    except Exception as e:
        print("Send function exception:", str(e))

# === ROUTES ===

# /track API called by Roblox script
@app.route('/track/<user_id>/<username>/<display>')
def track(user_id, username, display):
    USERS[user_id] = {
        'username': username,
        'display': display,
        'time': time.time()
    }
    save_users(USERS)

    # Telegram message with inline buttons
    buttons = [
        [{'text': '🚫 Ban', 'callback_data': f'ban_{user_id}'}],
        [{'text': '♻️ Unban', 'callback_data': f'unban_{user_id}'}]
    ]
    send(f"⚡ Script Executed by {display} (@{username})\nID: {user_id}", buttons)

    return "OK"

# Telegram callback query handler
@app.route('/callback', methods=['POST'])
def callback():
    try:
        data = request.get_json()
        if 'callback_query' in data:
            cq = data['callback_query']
            action, user_id = cq['data'].split('_')
            username, display = get_user_info(user_id)

            if action == 'ban':
                BLOCKED[user_id] = {'perm': True, 'msg': 'Banned via button'}
                save_blocked(BLOCKED)
                send(f"✅ {display} (@{username}) banned successfully")
            elif action == 'unban':
                BLOCKED.pop(user_id, None)
                save_blocked(BLOCKED)
                send(f"♻️ {display} (@{username}) unbanned successfully")
    except Exception as e:
        print("Callback error:", str(e))
    return "OK"

# /check API for Roblox script ban status
@app.route('/check/<user_id>', methods=['GET', 'POST'])
def check(user_id):
    cleanup_expired()
    data = BLOCKED.get(user_id, {})
    if data.get('perm') or (not data.get('perm') and time.time() < data.get('expire', 0)):
        return "true"
    return "false"

# /reason API for kick message
@app.route('/reason/<user_id>')
def get_reason(user_id):
    cleanup_expired()
    data = BLOCKED.get(user_id, {})
    if data and (data.get('perm') or time.time() < data.get('expire', 0)):
        return data.get('msg', 'Banned by Admin')
    return ""

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)