# Darija Anti‑Incitement Discord Bot (starter)

Detects/flags messages that *incite violence* in Moroccan Darija (Arabic + Arabizi) and English/French. 
Two-tier pipeline: fast moderation API + Darija-aware normalization/transliteration. 
Ships with **soft actions** (warn, delete) and **escalation** to a moderator queue; optional **timeout** (temp-mute) and **ban**.
Use this as a **starting point** and fine-tune thresholds/rules for your community.

## Features
- Normalizes Arabizi → Arabic (heuristic transliteration + cleanup).
- Calls an external moderation API (OpenAI Moderation) for quick violence/threat scoring.
- Simple **incitement heuristics** (Darija/Arabizi lexicon) + context window (previous messages in channel).
- Configurable actions: warn, delete, timeout, ban; and a moderator-review channel.
- JSONL audit log for every flagged decision.
- Slash command `/incitement review` to get last N flagged items (owner/mod only).

## Quick start

### 0) Discord bot setup
1. Create a bot at https://discord.com/developers/applications → **Bot**.
2. Under **Privileged Gateway Intents**, enable **Message Content Intent**.
3. Invite the bot to your server with permissions: **Read Messages**, **Send Messages**, **Manage Messages**, **Moderate Members** (for timeouts), **Ban Members** (optional).

### 1) Local setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env with your keys and server IDs
```

### 2) Configure `.env`
- `DISCORD_BOT_TOKEN`: your bot token
- `OPENAI_API_KEY`: key for the moderation API (optional if you disable Tier A)
- `MOD_QUEUE_CHANNEL_ID`: numeric channel ID to receive escalation messages (required for review flow)
- `OWNER_USER_ID`: your Discord user ID (enables admin commands)
- Thresholds and actions are also configurable (see below).

### 3) Run
```bash
python bot.py
```

## Environment variables (in `.env`)
```
DISCORD_BOT_TOKEN=
OPENAI_API_KEY=
MOD_QUEUE_CHANNEL_ID=123456789012345678
OWNER_USER_ID=123456789012345678

# thresholds (0.0–1.0)
THRESH_TEMP_MUTE=0.65
THRESH_ESCALATE=0.85
THRESH_AUTO_BAN=0.95

# actions toggles
ACTION_DELETE_MESSAGE=true
ACTION_WARN_USER=true
ACTION_TEMP_MUTE=true
ACTION_AUTO_BAN=false

# durations (seconds)
TEMP_MUTE_SECONDS=1800
CONTEXT_WINDOW=2
```

## What the scores mean
- `violence_score` from the moderation API estimates threats/violence likelihood (0–1).
- Heuristics add a small bonus when explicit Darija incitement verbs appear (e.g., *drebhoum*, *7rq*, *n9tel*, *t3awnou tderbou*).

## Policy recommendations
- Use **warn + delete** as the default first action.
- Reserve **timeout** for repeated or high-confidence cases.
- Only **ban** with human review unless you’re sure and your policy allows it.
- Publish your moderation policy in a pinned post and provide an appeal channel.

## Extending to a stronger model
- Replace/augment `moderation.py:openai_moderate` with your own fine-tuned MARBERT/XLM-R classifier.
- Connect a Hugging Face Inference Endpoint and map its logits → `incitement_score`.

## Disclaimer
This starter is not perfect. Dialect, sarcasm, and metaphor are tricky. Keep humans in the loop for irreversible actions.
