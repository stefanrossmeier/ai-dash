# Project independence

AI Dash owns its application configuration, prompts, Windmill stack, database,
Telegram credentials, private data and LLM gateway policy/state. It shares no
runtime service, checkout, credential mount, network or CLI profile with DailyDash.
The reusable gateway package/image is an independent dependency, not another
application's runtime. Provider revocation/billing isolation additionally requires
separately issued upstream keys.

All inference routes use the authenticated project gateway. X timeline collection
uses free RSS and has no paid retrieval fallback. The application worker carries
its own Telegram credentials and gateway bearer, never provider credentials.
