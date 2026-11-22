# X retrieval: RSS only

Normal X retrieval uses free Nitter RSS feeds. The paid OpenRouter X service,
client routing, budget implementation and cache-seeding script were removed in
the dedicated `Remove dormant paid X retrieval` commit. That commit can be
reverted or inspected if paid retrieval is reconsidered. Existing private audit
and accounting data are preserved; no reservations or history were reset.

Chat-based ranking still uses the project-owned LLM gateway and may incur cost.
