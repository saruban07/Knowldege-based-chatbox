# Discord KB Support Bot — Team Setup Guide

Complete setup and testing instructions for developers.

---

## What This Bot Does

- Answers support questions in Discord using **RAG** (retrieval over Markdown KB articles)
- Uses **semantic + keyword search** with query expansion for accurate retrieval
- Uses **Groq** for LLM answers (free tier)
- Uses **local ONNX embeddings** via ChromaDB (no extra API key)
- Escalates to a support ticket when confidence is below threshold
- Tracks answer and ticket analytics via `!analytics`

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Check with `python --version` |
| Git | Any recent | To clone the repo |
| Discord account | — | To create a test bot |
| Groq account | — | Free at https://console.groq.com |

**Internet needed on first run** to download the embedding model (~80 MB, cached locally).

---

## Step 1 — Clone and enter the project

```bash
git clone <your-repo-url>
cd bot
```

---

## Step 2 — Create a virtual environment

### Windows (PowerShell / CMD)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Step 3 — Get API keys

### A. Discord bot token

1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it (e.g. `KB Support Bot Dev`)
3. Open **Bot** (left sidebar) → **Reset Token** → copy the token
4. Under **Privileged Gateway Intents**, enable:
   - **Message Content Intent** (required)
5. Save changes

### B. Groq API key

1. Go to https://console.groq.com/keys
2. Sign up / log in
3. Click **Create API Key** → copy the key

---

## Step 4 — Configure environment

Copy the example env file and fill in your keys:

### Windows

```powershell
copy .env.example .env
notepad .env
```

### macOS / Linux

```bash
cp .env.example .env
nano .env   # or use your editor
```

### `.env` template

```env
DISCORD_TOKEN=your_discord_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=all-MiniLM-L6-v2
CONFIDENCE_THRESHOLD=0.75
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_TOKEN` | Yes | — | Discord bot token |
| `GROQ_API_KEY` | Yes | — | Groq API key |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq chat model |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Local ONNX embedding model |
| `CONFIDENCE_THRESHOLD` | No | `0.75` | Below this → offer ticket escalation |


**Never commit `.env`** — it is already in `.gitignore`.

---

## Step 5 — Invite the bot to a test server

1. In Discord Developer Portal → **OAuth2** → **URL Generator**
2. Scopes: `bot`
3. Bot permissions:
   - View Channels
   - Send Messages
   - Read Message History
4. Copy the generated URL, open it in a browser, and add the bot to your test server

---

## Step 6 — Verify setup

With the virtual environment activated:

```bash
python check_setup.py
```

Expected output:

```
[OK] DISCORD_TOKEN is set
[OK] GROQ_API_KEY is set (chat: llama-3.3-70b-versatile, embeddings: all-MiniLM-L6-v2)
[OK] 4 KB article(s) found
[OK] langchain-groq installed
[OK] local ONNX embeddings available (via chromadb)
[OK] discord.py installed

All checks passed. Run: python bot.py
```

---

## Step 7 — Run the bot

```bash
python bot.py
```

Expected startup:

```
Starting Discord KB Support Bot...
Loading libraries...
[1/4] Checking configuration...
  Groq configured (model: llama-3.3-70b-versatile)
[2/4] Initializing RAG service...
[3/4] Indexing knowledge base (local embeddings)...
  Ready — 4 KB files, 19 chunks indexed.
[4/4] Connecting to Discord...
```

When you see `Logged in as ...`, the bot is online.

Stop the bot with `Ctrl+C`.

---

## Quick setup scripts (optional)

Automated install for your team:

### Windows

```powershell
.\setup.ps1
```

### macOS / Linux

```bash
chmod +x setup.sh
./setup.sh
```

These scripts create the venv, install dependencies, copy `.env.example` → `.env` if missing, and run `check_setup.py`.

---
