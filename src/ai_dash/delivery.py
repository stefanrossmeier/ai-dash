from __future__ import annotations

import time

import httpx

from ai_dash.storage import Store


class Telegram:
    def __init__(self, token: str):
        self.base = "https://api.telegram.org/bot" + token.strip()

    def call(self, method: str, data: dict) -> dict:
        try:
            response = httpx.post(self.base + "/" + method, json=data, timeout=30)
        except httpx.HTTPError:
            # httpx errors include bot-token URLs. Never propagate those strings.
            raise RuntimeError("Telegram transport failed; delivery may be uncertain") from None
        try:
            result = response.json()
        except ValueError:
            raise RuntimeError("Telegram returned an invalid response") from None
        if not result.get("ok"):
            # Telegram rejected the request; 429 is safe to retry after its explicit delay.
            if result.get("error_code") == 429:
                raise RateLimited(
                    min(120, max(1, int(result.get("parameters", {}).get("retry_after", 5))))
                )
            raise Rejected(
                f"Telegram rejected request (code {result.get('error_code', response.status_code)})"
            )
        return result["result"]

    def check(self, destination: str):
        bot = self.call("getMe", {})
        chat = self.call("getChat", {"chat_id": destination})
        if chat.get("type") != "channel":
            raise ValueError("ai-dash requires a separate Telegram channel")
        member = self.call("getChatMember", {"chat_id": destination, "user_id": bot["id"]})
        if member.get("status") != "creator" and not (
            member.get("status") == "administrator" and member.get("can_post_messages")
        ):
            raise ValueError("bot needs channel administrator permission to post messages")
        return {"title": chat.get("title"), "type": chat["type"], "bot": bot["username"]}


class Rejected(RuntimeError):
    pass


class RateLimited(RuntimeError):
    def __init__(self, seconds: int):
        self.seconds = seconds


def flush(store: Store, telegram: Telegram, destination: str) -> int:
    pending = store.pending()
    if any(state == "sending" for _, _, _, state, _ in pending):
        raise RuntimeError("uncertain Telegram delivery: inspect channel and use resolve-delivery")
    if any(target != destination for _, _, _, _, target in pending):
        raise RuntimeError("pending outbox belongs to another destination; refusing to reroute")
    sent = 0
    for run_id, part, body, _, _ in pending:
        for attempt in range(3):
            store.mark(run_id, part, "sending")
            try:
                result = telegram.call(
                    "sendMessage",
                    {
                        "chat_id": destination,
                        "text": body,
                        "link_preview_options": {"is_disabled": True},
                    },
                )
            except RateLimited as exc:
                store.mark(run_id, part, "pending")
                if attempt == 2:
                    raise RuntimeError("Telegram rate limit persists") from None
                time.sleep(exc.seconds)
                continue
            except Rejected:
                store.mark(run_id, part, "pending")
                raise
            # On transport failure or process crash, 'sending' remains for operator resolution.
            store.mark(run_id, part, "sent", result["message_id"])
            sent += 1
            time.sleep(1)
            break
    return sent
