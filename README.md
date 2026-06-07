# Discord Knowledge Base Support Bot

L0 self-service support chatbot for Discord. Answers questions from Markdown KB articles using **RAG** (Retrieval-Augmented Generation), with automatic ticket escalation when confidence is low.

---

## Stack (mostly free)

| Component | Technology | Cost |
|-----------|------------|------|
| Discord bot | discord.py | Free |
| Embeddings | ChromaDB ONNX (`all-MiniLM-L6-v2`) | Free |
| Vector DB | ChromaDB (local) | Free |
| LLM | Groq API (`llama-3.3-70b-versatile`) | Free tier |
| Tickets | JSON file | Free |
| Analytics | JSON file | Free |

---

## Architecture Overview

```
User message (Discord)
        │
        ▼
  bot.py — on_message()
        │
        ▼
  RAG Pipeline (rag/llm.py)
        │
        ├── 1. Retriever (rag/retriever.py)
        │       ├── Query expansion (keyword aliases)
        │       ├── Semantic search (ChromaDB cosine similarity)
        │       └── Merge + filter by similarity threshold (≥ 0.20)
        │
        ├── 2. Embeddings (rag/embeddings.py)
        │       └── Local ONNX model via ChromaDB (no API key)
        │
        ├── 3. Loader (rag/loader.py)
        │       ├── Parses Markdown KB files by ## section
        │       ├── Extracts "Also known as" aliases per section
        │       └── Prepends aliases to every sub-chunk before indexing
        │
        └── 4. LLM (Groq API)
                └── Returns JSON: answer + citations + llm_confidence
                        │
                        ▼
              Confidence scoring
              (retrieval × 0.40 + chunk support × 0.25 + LLM × 0.35)
                        │
               ┌────────┴────────┐
           ≥ 75%              < 75%
               │                  │
          Answer sent        Offer ticket
          to user            escalation
                                  │
                           User confirms
                                  │
                        tickets/tickets.json
                                  │
                        analytics/analytics.json
```

**How retrieval works**

The bot uses a two-layer strategy so alternate phrasings still find the right KB section:

1. **Semantic search** — every KB chunk is embedded and stored in ChromaDB. Queries are matched by cosine similarity.
2. **Query expansion** — common support phrasings are automatically expanded before search. For example, `how to delete my account` also searches `remove account`, `close account`, `cancel account`, and `permanently delete`. Results from all variants are merged, keeping the best score per chunk.

KB authors can also add an `Also known as:` bullet list inside any section. The loader attaches these aliases to every chunk from that section so retrieval always finds them regardless of how the user phrases the question.

---

## Setup

> Full setup and testing guide with troubleshooting: [SETUP.md](SETUP.md)

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| Discord account | — |
| Groq account | Free at https://console.groq.com |

### Quick start

```bash
# Windows
.\setup.ps1

# macOS / Linux
chmod +x setup.sh && ./setup.sh
```

Then edit `.env` with your keys (see below) and run:

```bash
python bot.py
```

### Required API keys

| Key | Where to get it |
|-----|-----------------|
| `DISCORD_TOKEN` | [Discord Developer Portal](https://discord.com/developers/applications) → Bot → Reset Token |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) → Create API Key |

### Environment variables

Copy `.env.example` to `.env` and fill in your values:

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
| `GROQ_API_KEY` | Yes | — | Groq LLM API key |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model to use |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Local ONNX embedding model |
| `CONFIDENCE_THRESHOLD` | No | `0.75` | Below this score → offer ticket escalation |

**Never commit `.env`** — it is already in `.gitignore`.

### Discord bot permissions

In the Discord Developer Portal under **Privileged Gateway Intents**, enable:
- **Message Content Intent** (required — bot cannot read messages without this)

Bot permissions needed when inviting: View Channels, Send Messages, Read Message History.

---

## Run Instructions

```bash
# Activate virtual environment first
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Start the bot
python bot.py
```

Expected startup output:

```
Starting Discord KB Support Bot...
[1/4] Checking configuration...
  Groq configured (model: llama-3.3-70b-versatile)
[2/4] Initializing RAG service...
[3/4] Indexing knowledge base (local embeddings)...
  Ready — 4 KB files, 19 chunks indexed.
[4/4] Connecting to Discord...
```

When you see `Logged in as ...` the bot is live. Stop with `Ctrl+C`.

### After changing KB articles

```
!reindex
```

This rebuilds the vector index from `kb/*.md` without restarting the bot.

---

## Usage

Ask support questions in any channel without a command prefix:

```
How do I reset my password?
How do I delete my account?
What subscription plans are available?
```

### Commands

| Command | Description |
|---------|-------------|
| `!help` | Show all commands |
| `!stats` | KB files, indexed chunks, ticket count, model info |
| `!reindex` | Rebuild vector DB after KB changes |
| `!ticket <question>` | Manually create a support ticket |
| `!analytics` | Show questions answered, escalation rate, avg confidence, top questions |

### Ticket escalation flow

When the bot cannot answer confidently (score < 75%), it asks the user to confirm a ticket:

```
User:  how do I delete my account?
Bot:   I couldn't confidently answer this. Confidence: 42%
       Would you like me to create a support ticket? Reply yes to confirm.
User:  yes
Bot:   Support ticket created. Ticket #1001 ...
```

---

## Project Structure

```
bot/
├── bot.py                   # Discord bot — events, commands, escalation flow
├── check_setup.py           # Pre-flight environment checks
├── setup.ps1                # Windows automated setup script
├── setup.sh                 # macOS/Linux automated setup script
├── SETUP.md                 # Full team setup and testing guide
├── requirements.txt
├── .env.example             # Environment variable template
├── .env                     # Your secrets (not committed)
├── rag/
│   ├── loader.py            # Markdown parser, section chunker, alias extractor
│   ├── embeddings.py        # Local ONNX embeddings + ChromaDB vector store
│   ├── retriever.py         # Semantic search + query expansion + score merging
│   ├── prompts.py           # LLM system prompt and user prompt builder
│   └── llm.py               # Groq RAG pipeline, confidence scoring, response formatter
├── analytics/
│   └── manager.py           # Question logging, escalation tracking, stats
├── tickets/
│   └── tickets.json         # Persisted support tickets
├── kb/                      # Markdown knowledge base articles
└── chroma_db/               # ChromaDB vector index (auto-generated, not committed)
```

---

## Test Results

Run the test suite:

```bash
pytest tests/ -v
```

Output:

```
platform win32 -- Python 3.12.8, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\LENOVO\Desktop\project\Knowldege-based-chatbox
plugins: anyio-4.4.0, langsmith-0.8.9
collected 29 items

tests/test_happy_path.py::TestLoader::test_document_chunk_fields PASSED              [  3%]
tests/test_happy_path.py::TestLoader::test_parse_sections_splits_on_headings PASSED  [  6%]
tests/test_happy_path.py::TestLoader::test_extract_aliases_returns_list PASSED       [ 10%]
tests/test_happy_path.py::TestLoader::test_aliases_prepended_to_chunk_content PASSED [ 13%]
tests/test_happy_path.py::TestLoader::test_load_kb_documents_returns_chunks PASSED   [ 17%]
tests/test_happy_path.py::TestLoader::test_empty_kb_directory_returns_empty_list PASSED [ 20%]
tests/test_happy_path.py::TestQueryExpansion::test_original_query_always_included PASSED [ 24%]
tests/test_happy_path.py::TestQueryExpansion::test_delete_trigger_expands PASSED     [ 27%]
tests/test_happy_path.py::TestQueryExpansion::test_no_trigger_returns_single_variant PASSED [ 31%]
tests/test_happy_path.py::TestQueryExpansion::test_retriever_filters_below_threshold PASSED [ 34%]
tests/test_happy_path.py::TestQueryExpansion::test_retriever_accepts_above_threshold PASSED [ 37%]
tests/test_happy_path.py::TestQueryExpansion::test_retrieval_result_avg_similarity PASSED [ 41%]
tests/test_happy_path.py::TestJsonParsing::test_parses_clean_json PASSED             [ 44%]
tests/test_happy_path.py::TestJsonParsing::test_strips_markdown_fences PASSED        [ 48%]
tests/test_happy_path.py::TestJsonParsing::test_handles_literal_newline_in_string PASSED [ 51%]
tests/test_happy_path.py::TestJsonParsing::test_fallback_on_plain_text PASSED        [ 55%]
tests/test_happy_path.py::TestJsonParsing::test_extracts_json_from_mixed_text PASSED [ 58%]
tests/test_happy_path.py::TestConfidenceScoring::test_high_confidence_all_signals PASSED [ 62%]
tests/test_happy_path.py::TestConfidenceScoring::test_low_confidence_poor_retrieval PASSED [ 65%]
tests/test_happy_path.py::TestConfidenceScoring::test_score_clamped_between_0_and_1 PASSED [ 68%]
tests/test_happy_path.py::TestTicketManager::test_create_ticket_returns_ticket PASSED [ 72%]
tests/test_happy_path.py::TestTicketManager::test_ticket_id_increments PASSED        [ 75%]
tests/test_happy_path.py::TestTicketManager::test_ticket_persisted_to_json PASSED    [ 79%]
tests/test_happy_path.py::TestTicketManager::test_ticket_count_property PASSED       [ 82%]
tests/test_happy_path.py::TestTicketManager::test_ticket_has_timestamp PASSED        [ 86%]
tests/test_happy_path.py::TestTicketManager::test_ticket_stores_user_id PASSED       [ 89%]
tests/test_happy_path.py::TestTicketManager::test_multiple_tickets_persisted PASSED  [ 93%]
tests/test_happy_path.py::TestTicketManager::test_next_id_increments_in_json PASSED  [ 96%]
tests/test_happy_path.py::TestTicketManager::test_format_ticket_message PASSED       [100%]

29 passed in 3.11s
```

### Test Coverage

| Module | Tests | What is verified |
|--------|-------|-----------------|
| `rag/loader.py` | 6 | Chunking, alias extraction, alias prepended to chunks, empty KB |
| `rag/retriever.py` | 6 | Query expansion, similarity filtering, avg similarity calculation |
| `rag/llm.py` | 8 | JSON parsing, fence stripping, newline crash fix, confidence scoring |
| `tickets/manager.py` | 9 | Create ticket, ID increment, JSON persistence, timestamp, analytics |

All 29 tests run fully offline — no Discord token, Groq API key, or ChromaDB required.

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

---

## Assumptions and Limitations

### Assumptions

- **KB articles are Markdown files** structured with `##` section headings. The loader splits on these headings; flat or heading-free files are treated as a single chunk.
- **Groq free tier is sufficient** for the expected query volume. The bot makes one LLM call per user question.
- **Local embeddings are acceptable** — `all-MiniLM-L6-v2` runs on CPU via ONNX. It is fast and requires no API key but is a smaller model than hosted alternatives, so semantic coverage on unusual phrasings may be weaker.
- **A single Discord server** — the bot is designed for one server. Running it across multiple servers simultaneously is untested.
- **English-language KB** — the embedding model and prompts are optimised for English. Other languages will work but retrieval quality may degrade.

### Limitations

- **No conversation memory** — each message is processed independently. The bot has no context from previous messages in the same conversation.
- **Knowledge cutoff is the KB** — the bot only knows what is in `kb/*.md`. It cannot browse the web or answer questions outside the KB.
- **Confidence scoring is heuristic** — the composite score (retrieval similarity + chunk count + LLM self-reported confidence) is an approximation. It can produce false positives (escalating an answerable question) or false negatives (answering with low accuracy).
- **Groq rate limits** — the free tier allows ~30 requests per minute. Under high load, requests may be delayed or fail with a 429 error. The bot retries twice then returns an error message.
- **ChromaDB is local** — the vector index lives on disk in `chroma_db/`. It is not shared between team members. Each developer must run `!reindex` on their own machine.
- **Analytics reset on restart** — question counts and escalation stats are tracked in memory and written to `analytics/analytics.json`. If the file is absent on startup, stats begin from zero.
- **Single-file ticket storage** — tickets are stored in `tickets/tickets.json`. Concurrent writes from multiple bot instances could corrupt the file. This is suitable for a single-instance deployment only.

---

## License

MIT