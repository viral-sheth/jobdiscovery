"""Print your Telegram chat id.

1. Open Telegram and send any message to your bot.
2. Run:  python get_chat_id.py
3. Paste the printed id into .env as TELEGRAM_CHAT_ID.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    raise SystemExit("TELEGRAM_BOT_TOKEN is not set in .env")

resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30)
resp.raise_for_status()
updates = resp.json().get("result", [])

chats = {}
for update in updates:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat")
    if chat:
        chats[chat["id"]] = chat

if not chats:
    print("No messages found. Send your bot a message in Telegram, then rerun this script.")
else:
    for chat_id, chat in chats.items():
        name = chat.get("username") or chat.get("first_name") or chat.get("title") or "?"
        print(f"TELEGRAM_CHAT_ID={chat_id}   (chat with: {name})")
