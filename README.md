# Discord Knowledge Base Support Bot

L0 self-service support chatbot for Discord. Answers questions from Markdown KB articles using **RAG**, with ticket escalation when confidence is low.

## Stack (mostly free)

| Component | Technology | Cost |
|-----------|------------|------|
| Discord bot | discord.py | Free |
| Embeddings | ChromaDB ONNX (local) | Free |
| Vector DB | ChromaDB (local) | Free |
| LLM | **Groq API** | **Free tier** |
| Tickets | JSON file | Free |

## Team setup

**Full setup and testing guide:** [SETUP.md](SETUP.md)

### Quick start

```bash
# Windows
.\setup.ps1

# macOS / Linux
chmod +x setup.sh && ./setup.sh
```

Then edit `.env` with your keys and run:

```bash
python bot.py
```

### Required keys

| Key | Where to get it |
|-----|-----------------|
| `DISCORD_TOKEN` | [Discord Developer Portal](https://discord.com/developers/applications) |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) |

## Usage

Ask in any channel (no command prefix):

```
How do I reset my password?
```

### Commands

| Command | Description |
|---------|-------------|
| `!help` | Show commands |
| `!reindex` | Rebuild vector DB after KB changes |
| `!stats` | KB files, chunks, tickets, models |
| `!ticket <question>` | Create support ticket manually |

## Project structure

```
bot/
├── bot.py
├── SETUP.md               # Full team setup guide
├── setup.ps1 / setup.sh   # Automated setup scripts
├── rag/
│   ├── loader.py
│   ├── embeddings.py
│   ├── retriever.py
│   ├── prompts.py
│   └── llm.py
├── kb/                    # Markdown articles
├── tickets/tickets.json
├── chroma_db/
├── check_setup.py
├── .env
└── requirements.txt
```

## License

MIT
