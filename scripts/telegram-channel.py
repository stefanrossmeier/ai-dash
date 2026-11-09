"""Read-only setup helper for the NEW ai-dash bot. Never logs token/message content."""

import json
import urllib.request
from pathlib import Path

path = Path("/var/code/ai-dash-runtime/secrets/telegram_token")
try:
    token = path.read_text().strip()
    if not token:
        raise ValueError("empty token")

    def call(method):
        request = urllib.request.Request(
            "https://api.telegram.org/bot" + token + "/" + method,
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        data = json.load(urllib.request.urlopen(request, timeout=20))
        if not data.get("ok"):
            raise ValueError("Telegram rejected request")
        return data["result"]

    if call("getWebhookInfo").get("url"):
        raise ValueError(
            "This bot has a webhook; inspect channel setup through its update consumer."
        )
    channels = {}
    for update in call("getUpdates"):
        for key in ["channel_post", "edited_channel_post", "my_chat_member"]:
            chat = update.get(key, {}).get("chat", {})
            if chat.get("type") == "channel":
                channels[chat["id"]] = chat.get("title", "")
    print(json.dumps(channels, indent=2))
except Exception:
    raise SystemExit(
        "Channel lookup failed. Check token file, network and webhook setup; credentials omitted."
    ) from None
