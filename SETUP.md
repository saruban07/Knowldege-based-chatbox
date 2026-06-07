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

## How semantic + keyword search works

The bot uses a two-layer retrieval strategy to find the right KB content even when the user's phrasing doesn't exactly match the documentation.

**Layer 1 — semantic search (dense embeddings)**
Every KB chunk is embedded using `all-MiniLM-L6-v2` and stored in ChromaDB. When a question arrives, its embedding is compared against all chunks using cosine similarity. Chunks scoring above `0.20` similarity are kept.

**Layer 2 — query expansion (keyword aliases)**
Common support phrasings are automatically expanded into multiple search variants before retrieval. For example:

| User types | Variants searched |
|---|---|
| `how to delete my account` | + `remove account`, `close account`, `cancel account`, `permanently delete` |
| `reset password` | + `forgot password`, `change password` |
| `two factor` | + `2fa`, `two-factor authentication` |

Results from all variants are merged, keeping the best similarity score per chunk. This means queries like "remove my account" or "cancel my account permanently" correctly retrieve the **Deleting Your Account** section even though the heading uses different wording.

**Why this matters for KB authors**
Each KB section can include an `Also known as:` bullet list of alternate phrasings. The loader attaches these aliases to every chunk from that section so they are always present during retrieval:

```markdown
## Deleting Your Account
Also known as:
- Remove account
- Close account
- Cancel my account permanently

1. Go to **Settings** > **Account** > **Danger Zone**...
```

This eliminates most retrieval misses without requiring any code changes — just update the KB file and run `!reindex`.

---

## Testing checklist

Use a dedicated `#bot-testing` channel in your Discord server.

### 1. Bot is online

- [ ] Bot shows as online in the member list
- [ ] `!help` returns the command embed

### 2. Stats command

Send:

```
!stats
```

- [ ] Shows **4** KB files
- [ ] Shows indexed chunks (≈19)
- [ ] Shows LLM: `llama-3.3-70b-versatile`
- [ ] Shows Embeddings: `all-MiniLM-L6-v2`

### 3. Knowledge base Q&A (no command prefix)

Send these plain messages one at a time:

| # | Message | Expected |
|---|---------|----------|
| 1 | `How do I reset my password?` | Step-by-step answer + sources + confidence |
| 2 | `What subscription plans do you offer?` | Free / Pro / Enterprise pricing |
| 3 | `How do I connect Slack?` | Integration steps from `integrations.md` |
| 4 | `How do I delete my account?` | Danger Zone steps |
| 5 | `How do I view my invoice?` | Billing → Invoice History steps |

### 4. Semantic + keyword retrieval

Test that alternate phrasings retrieve the correct answer (these should not escalate):

| # | Message | Should answer from |
|---|---------|-------------------|
| 1 | `remove my account` | `account-management.md > Deleting Your Account` |
| 2 | `cancel my account permanently` | `account-management.md > Deleting Your Account` |
| 3 | `forgot password` | `password-reset.md` |
| 4 | `enable 2fa` | `account-management.md > Security Settings` |
| 5 | `change my display name` | `account-management.md > Updating Your Profile` |

If any of these escalate to a ticket, run `!reindex` and check that the relevant KB section contains an `Also known as:` block with the matching phrase.

### 5. Low-confidence escalation

Send something outside the KB:

```
What is the capital of France?
```

- [ ] Bot says it cannot answer confidently
- [ ] Bot asks if you want a support ticket
- [ ] Reply `yes` → ticket is created

### 6. Manual ticket

```
!ticket I need help with something not in the KB
```

- [ ] Ticket created with ID and question text

### 7. Analytics command

```
!analytics
```

- [ ] Shows total questions answered and escalated
- [ ] Shows average confidence score
- [ ] Shows top repeated questions
- [ ] Ticket resolution rate updates after tickets are created

### 8. Reindex after KB changes

1. Edit any file in `kb/` (or add a new `.md` file)
2. Send `!reindex`
3. Send `!stats` — chunk count should update
4. Ask a question about the new/edited content

---

## Sample questions by topic

The bot only knows what is in `kb/*.md`:

### Password reset (`kb/password-reset.md`)
- How do I reset my password?
- I forgot my password — what do I do?
- What are the password requirements?
- The reset email never arrived — what should I check?

### Billing (`kb/billing.md`)
- How do I download an invoice?
- How do I update my payment method?
- What plans are available?
- How do I cancel my subscription?

### Account management (`kb/account-management.md`)
- How do I enable 2FA?
- How do I update my profile?
- How do I delete my account?
- How do I transfer ownership?

### Integrations (`kb/integrations.md`)
- How do I set up Slack?
- How do I create a webhook?
- What are the API rate limits?
- How do I disconnect an integration?

### Security (`kb/security.md`)

* What are the password requirements?
* How is customer data encrypted?
* Is my data encrypted at rest?
* What encryption methods are used?
* How long before an inactive session expires?
* What is the session timeout period?
* What security measures are in place?
* How do you protect customer data?

### Reports (`kb/reports.md`)

* How do I generate a report?
* Where can I create reports?
* What report export formats are supported?
* Can I export reports as PDF?
* Can I download reports in Excel format?
* Can I export reports as CSV?
* How do scheduled reports work?
* Which plans support scheduled reports?
* Can reports be generated automatically?

### Notifications (`kb/notifications.md`)

* How do I manage email notifications?
* Where can I configure notification settings?
* What notification types are available?
* How do I enable push notifications?
* How do I disable push notifications?
* How do I unsubscribe from emails?
* Can I receive billing alerts?
* Can I receive security alerts?
* How do I get product update notifications?


---

## Commands reference

| Command | Who | Description |
|---------|-----|-------------|
| `!help` | Everyone | Show available commands |
| `!stats` | Everyone | KB files, chunks, tickets, models |
| `!analytics` | Everyone | Questions answered, escalated, avg confidence, top questions, ticket resolution rate |
| `!reindex` | Everyone | Rebuild vector DB from `kb/` |
| `!ticket <question>` | Everyone | Manually create a support ticket |

Plain messages (no `!`) are treated as support questions.

---

## Project structure

```
bot/
├── bot.py                   # Discord bot entry point
├── check_setup.py           # Pre-flight checks
├── setup.ps1                # Windows setup script
├── setup.sh                 # macOS/Linux setup script
├── SETUP.md                 # This file
├── requirements.txt
├── .env.example             # Template (copy to .env)
├── .env                     # Your secrets (not committed)
├── rag/
│   ├── loader.py            # Load & chunk KB markdown, alias extraction
│   ├── embeddings.py        # Local ONNX embeddings + ChromaDB
│   ├── retriever.py         # Semantic search + query expansion
│   ├── prompts.py           # LLM prompts
│   └── llm.py               # Groq RAG pipeline
├── analytics/
│   └── manager.py           # Question + escalation tracking
|   └── analytics.json
├── kb/                      # Knowledge base articles (.md)
├── tickets/
│   └── tickets.json         # Created support tickets
|   └── manager.py`
└── chroma_db/               # Vector index (auto-generated)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `GROQ_API_KEY is not set` | Copy `.env.example` to `.env` and add your Groq key |
| `DISCORD_TOKEN is not set` | Add Discord bot token to `.env` |
| `NameError: check_gemini_available` | Pull latest code — project uses Groq now |
| Bot online but no replies | Enable **Message Content Intent** in Discord Developer Portal |
| `Invalid DISCORD_TOKEN` | Reset token in Developer Portal, update `.env` |
| Groq 429 / rate limit | Wait and retry; free tier has limits |
| Slow first startup | Normal — embedding model downloads once (~80 MB) |
| Wrong or stale answers | Run `!reindex` after editing `kb/` files |
| Query like "remove account" escalates | Add it to the `Also known as:` block in the relevant KB section, then `!reindex` |
| `!analytics` shows 0 questions | Questions are tracked in memory; stats reset on bot restart |
| `KeyboardInterrupt` on stop | Normal when pressing `Ctrl+C` |


### Windows notes

- Use `cls` to clear terminal (not `clear`)
- Use `copy` instead of `cp`
- Activate venv: `venv\Scripts\activate`

---

## Team workflow

1. Each developer uses their **own** Discord bot + Groq keys in a local `.env`
2. Do **not** share tokens in Slack, email, or commits
3. After pulling KB changes from git, run `!reindex`
4. Check `bot.log` in the project root for errors
5. Tickets are stored in `tickets/tickets.json` (local, not committed by default)

---

## Adding new KB content

1. Add or edit a `.md` file in `kb/`
2. Use clear headings (`## Section Name`) — they become citation sources
3. Add an `Also known as:` block under headings where users may phrase things differently:

```markdown
## Deleting Your Account
Also known as:
- Remove account
- Close account
- Cancel my account permanently
```

4. Restart bot or run `!reindex` in Discord
5. Test with a question using an alternate phrasing from the alias list

---

## Security reminders

- `.env` is gitignored — keep it that way
- Rotate Discord token and Groq key if exposed
- Use a test Discord server, not production, during development

---

## Support

If setup fails after following this guide:

1. Run `python check_setup.py` and fix reported errors
2. Check `bot.log` for stack traces
3. Confirm Message Content Intent is enabled
4. Confirm the bot has channel permissions in your test server