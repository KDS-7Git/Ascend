"""Telegram transport. Credentials only come from the environment."""

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


def chat_id(user_id=1):
    return os.environ.get(f"TELEGRAM_CHAT_ID_{user_id}") or (
        os.environ.get("TELEGRAM_CHAT_ID") if user_id == 1 else None
    )


def call(method, payload):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Telegram bot token is not configured")
    try:
        request = Request(
            f"https://api.telegram.org/bot{token}/{method}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read())
        if not result.get("ok"):
            raise ValueError("Telegram rejected the request")
        return result
    except (URLError, OSError, json.JSONDecodeError):
        raise ValueError(
            "Telegram delivery failed; check the bot and chat configuration"
        ) from None


def send(message, user_id=1, actions=True, **config):
    chat = chat_id(user_id)
    if not chat:
        raise ValueError("Telegram chat ID is not configured")
    payload = {"chat_id": chat, "text": message}
    if actions:
        buttons = [
            [
                {"text": "Log a step", "callback_data": "ascend-log"},
                {"text": "Log quick win", "callback_data": "ascend-quick"},
            ]
        ]
        public_url = os.environ.get("ASCEND_PUBLIC_URL")
        if public_url and public_url.startswith("https://"):
            buttons.append([{"text": "Open Ascend", "url": public_url}])
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return call("sendMessage", payload)
