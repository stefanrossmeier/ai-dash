# Independent Telegram bot and channel

AI Dash has its OWN bot and channel. Do not reuse daily-dash's Telegram token or chat ID.

1. Open the verified `@BotFather` in Telegram, send `/newbot`, choose a display
   name and an available username ending in `bot`. Keep the issued token private.
2. Create a channel named **AI Dash**. Private is suitable for personal use.
3. Channel settings → Administrators → Add Administrator → select the NEW bot.
   Enable **Post Messages**. Other administrator powers are unnecessary.
4. Store its token on the VPS with the command below. Do not paste it into chat.

```bash
ssh your-vps
install -d -m 700 /var/code/ai-dash-runtime/secrets
read -rs -p 'New AI Dash bot token: ' AI_TOKEN; echo
printf '%s' "$AI_TOKEN" > /var/code/ai-dash-runtime/secrets/telegram_token
unset AI_TOKEN
chmod 600 /var/code/ai-dash-runtime/secrets/telegram_token
```

For a public channel, use its `@channelusername` as the destination. A private channel
needs its numeric chat ID (usually starts `-100`). After adding the bot, a channel
post or membership update can reveal that ID through Bot API `getUpdates`, provided
the bot has no webhook or another update consumer. The ai-dash sender does not poll
updates. See `scripts/telegram-channel.py`: it checks webhook status, lists ONLY
channel IDs/titles, and never prints a token or message contents. It does not advance
the update offset. If no update exists, post a short message in the new channel and rerun.

```bash
python3 /var/code/ai-dash/scripts/telegram-channel.py
read -r -p 'New AI Dash channel ID or @username: ' AI_CHAT
printf '%s' "$AI_CHAT" > /var/code/ai-dash-runtime/secrets/telegram_chat_id
unset AI_CHAT
chmod 600 /var/code/ai-dash-runtime/secrets/telegram_chat_id
```

Use the worker's `ai-dash check-telegram` command to verify that this is a channel
and that the bot has permission to publish, before enabling schedules.

Official references: [creating bots](https://core.telegram.org/bots/tutorial#obtain-your-bot-token),
[channels](https://telegram.org/faq_channels),
[Bot API](https://core.telegram.org/bots/api).
