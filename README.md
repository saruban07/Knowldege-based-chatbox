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