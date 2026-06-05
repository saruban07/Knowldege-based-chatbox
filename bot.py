"""
Discord Knowledge Base Support Bot.

L0 self-service support chatbot using RAG over Markdown KB articles.
Escalates to ticket creation when confidence is below threshold.
"""

from __future__ import annotations

print("Starting Discord KB Support Bot...", flush=True)
print("Loading libraries...", flush=True)

import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from rag.llm import RAGService, check_groq_available
from tickets.manager import TicketManager

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("support_bot")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
COMMAND_PREFIX = "!"

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN is not set. Copy .env.example to .env and fill in values.")
    sys.exit(1)

if not GROQ_API_KEY:
    logger.error(
        "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

rag_service: RAGService
ticket_manager: TicketManager

# Pending escalation: user_id -> original question
_pending_escalations: dict[int, str] = {}

YES_RESPONSES = {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "please", "create", "ticket"}


def _is_command(message: discord.Message) -> bool:
    return message.content.strip().startswith(COMMAND_PREFIX)


@bot.event
async def on_ready() -> None:
    logger.info("Logged in as %s (id=%s)", bot.user, bot.user.id if bot.user else "?")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="support questions | !help",
        )
    )


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    await bot.process_commands(message)

    if _is_command(message):
        return

    content = message.content.strip()
    if not content:
        return

    user_id = message.author.id

    # Handle pending ticket escalation confirmation
    if user_id in _pending_escalations and content.lower() in YES_RESPONSES:
        question = _pending_escalations.pop(user_id)
        await _create_and_reply_ticket(message, question)
        return

    await _handle_support_question(message, content)


async def _handle_support_question(message: discord.Message, question: str) -> None:
    """Process a natural-language support question via RAG."""
    user = message.author
    logger.info("Question from %s (%s): %s", user.display_name, user.id, question[:120])

    async with message.channel.typing():
        try:
            rag_response = await rag_service.answer(question)
        except Exception as exc:
            logger.exception("RAG pipeline error: %s", exc)
            await message.reply(
                "Something went wrong while processing your question. "
                "Please try again or use `!ticket <your question>` to escalate."
            )
            return

    logger.info(
        "Answer confidence=%.2f retrieval=%.2f chunks=%d user=%s",
        rag_response.confidence,
        rag_response.retrieval_similarity,
        rag_response.supporting_chunks,
        user.id,
    )

    if rag_service.should_escalate(rag_response.confidence):
        _pending_escalations[user.id] = question
        response = (
            "I couldn't confidently answer this from the knowledge base.\n"
            f"**Confidence:** {rag_response.confidence:.0%}\n\n"
            "Would you like me to create a support ticket? Reply **yes** to confirm, "
            "or use `!ticket <your question>`."
        )
        await message.reply(response)
        return

    formatted = rag_service.format_discord_response(rag_response)
    await message.reply(formatted)


async def _create_and_reply_ticket(message: discord.Message, question: str) -> None:
    try:
        ticket = ticket_manager.create_ticket(
            question=question,
            user_id=str(message.author.id),
            username=str(message.author.display_name),
            channel_id=str(message.channel.id),
        )
    except Exception as exc:
        logger.exception("Ticket creation failed: %s", exc)
        await message.reply("Failed to create a ticket. Please try again later.")
        return

    await message.reply(
        f"Support ticket created.\n\n{ticket_manager.format_ticket_message(ticket)}"
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@bot.command(name="help")
async def cmd_help(ctx: commands.Context) -> None:
    """Show available commands."""
    embed = discord.Embed(
        title="Knowledge Base Support Bot",
        description="Ask support questions in plain English, or use these commands:",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name=f"{COMMAND_PREFIX}help",
        value="Show this help message",
        inline=False,
    )
    embed.add_field(
        name=f"{COMMAND_PREFIX}reindex",
        value="Rebuild the vector database from KB articles",
        inline=False,
    )
    embed.add_field(
        name=f"{COMMAND_PREFIX}stats",
        value="Show KB files, indexed chunks, and ticket count",
        inline=False,
    )
    embed.add_field(
        name=f"{COMMAND_PREFIX}ticket <question>",
        value="Manually create a support ticket",
        inline=False,
    )
    embed.set_footer(text="Ask any support question without a command prefix.")
    await ctx.send(embed=embed)


@bot.command(name="reindex")
async def cmd_reindex(ctx: commands.Context) -> None:
    """Rebuild vector database from KB Markdown files."""
    await ctx.send("Reindexing knowledge base… This may take a moment.")
    try:
        file_count, chunk_count = await asyncio.to_thread(rag_service.reindex)
        await ctx.send(
            f"Reindex complete.\n"
            f"• KB files: **{file_count}**\n"
            f"• Indexed chunks: **{chunk_count}**"
        )
    except Exception as exc:
        logger.exception("Reindex failed: %s", exc)
        await ctx.send(f"Reindex failed: {exc}")


@bot.command(name="stats")
async def cmd_stats(ctx: commands.Context) -> None:
    """Show KB and ticket statistics."""
    embed = discord.Embed(title="Bot Statistics", color=discord.Color.green())
    embed.add_field(name="KB Files", value=str(rag_service.kb_file_count), inline=True)
    embed.add_field(name="Indexed Chunks", value=str(rag_service.indexed_chunks), inline=True)
    embed.add_field(name="Tickets", value=str(ticket_manager.ticket_count), inline=True)
    embed.add_field(name="LLM (Groq)", value=GROQ_MODEL, inline=True)
    embed.add_field(name="Embeddings", value=EMBEDDING_MODEL, inline=True)
    embed.add_field(
        name="Confidence Threshold",
        value=f"{CONFIDENCE_THRESHOLD:.0%}",
        inline=True,
    )
    await ctx.send(embed=embed)


@bot.command(name="ticket")
async def cmd_ticket(ctx: commands.Context, *, question: str | None = None) -> None:
    """Manually create a support ticket."""
    if not question or not question.strip():
        await ctx.send(
            f"Usage: `{COMMAND_PREFIX}ticket <your question>`\n"
            "Example: `!ticket I can't access my billing dashboard`"
        )
        return

    _pending_escalations.pop(ctx.author.id, None)
    await _create_and_reply_ticket(ctx.message, question.strip())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    global rag_service, ticket_manager

    print("[1/4] Checking configuration...", flush=True)
    Path("kb").mkdir(exist_ok=True)
    Path("tickets").mkdir(exist_ok=True)
    Path("chroma_db").mkdir(exist_ok=True)

    ok, groq_msg = check_groq_available(GROQ_API_KEY, GROQ_MODEL)
    if not ok:
        logger.error(groq_msg)
        print(f"\n[SETUP REQUIRED] {groq_msg}\n", flush=True)
        sys.exit(1)
    logger.info(groq_msg)
    print(f"  {groq_msg}", flush=True)

    print("[2/4] Initializing RAG service...", flush=True)
    ticket_manager = TicketManager()
    rag_service = RAGService(
        model_name=GROQ_MODEL,
        groq_api_key=GROQ_API_KEY,
        confidence_threshold=CONFIDENCE_THRESHOLD,
    )

    print("[3/4] Indexing knowledge base (local embeddings)...", flush=True)
    logger.info("Initializing RAG service (Groq LLM + local embeddings)…")
    rag_service.initialize()
    logger.info(
        "Ready — %d KB files, %d chunks, %d tickets",
        rag_service.kb_file_count,
        rag_service.indexed_chunks,
        ticket_manager.ticket_count,
    )
    print(
        f"  Ready — {rag_service.kb_file_count} KB files, "
        f"{rag_service.indexed_chunks} chunks indexed.",
        flush=True,
    )

    print("[4/4] Connecting to Discord...", flush=True)
    try:
        bot.run(DISCORD_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("Invalid DISCORD_TOKEN. Check your .env file.")
        print(
            "\n[DISCORD LOGIN FAILED]\n"
            "Your bot token is invalid or was reset. Fix it:\n"
            "  1. Go to https://discord.com/developers/applications\n"
            "  2. Select your app → Bot → Reset Token\n"
            "  3. Copy the NEW token into .env as DISCORD_TOKEN=\n"
            "  4. Enable 'Message Content Intent' under Bot settings\n"
            "  5. Run: python bot.py\n",
            flush=True,
        )
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        logger.error("Message Content Intent is not enabled in Discord Developer Portal.")
        print(
            "\n[PRIVILEGED INTENT REQUIRED]\n"
            "The bot needs 'Message Content Intent' to read your messages. Enable it:\n"
            "  1. Go to https://discord.com/developers/applications\n"
            "  2. Select your app → Bot (left sidebar)\n"
            "  3. Scroll to 'Privileged Gateway Intents'\n"
            "  4. Turn ON 'Message Content Intent'\n"
            "  5. Click Save Changes\n"
            "  6. Run: python bot.py\n",
            flush=True,
        )
        sys.exit(1)
    except Exception as exc:
        logger.exception("Bot crashed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
