"""Verify setup is ready before starting the bot."""

from __future__ import annotations
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def main() -> int:
    print("Discord KB Support Bot — setup check\n")
    errors: list[str] = []
    warnings: list[str] = []

    token = os.getenv("DISCORD_TOKEN", "")

    if not token or token == "your_discord_bot_token_here":
        errors.append("DISCORD_TOKEN is missing in .env")
    else:
        print("[OK] DISCORD_TOKEN is set")

    groq_key = os.getenv("GROQ_API_KEY", "")

    if not groq_key or groq_key == "your_groq_api_key_here":
        errors.append(
            "GROQ_API_KEY is missing — get free key at https://console.groq.com/keys"
        )

    else:
        chat_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        embed_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        print(f"[OK] GROQ_API_KEY is set (chat: {chat_model}, embeddings: {embed_model})")

    kb_dir = Path("kb")

    md_files = list(kb_dir.glob("*.md")) if kb_dir.exists() else []

    if not md_files:
        warnings.append("No .md files in kb/ — add articles before asking questions")
    else:
        print(f"[OK] {len(md_files)} KB article(s) found")

    try:
        from langchain_groq import ChatGroq  # noqa: F401
        print("[OK] langchain-groq installed")

    except ImportError:
        errors.append("langchain-groq not installed — run: pip install -r requirements.txt")

    try:
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2  # noqa: F401
        print("[OK] local ONNX embeddings available (via chromadb)")

    except ImportError:
        errors.append("chromadb embeddings not available — run: pip install -r requirements.txt")

    try:
        import discord  # noqa: F401
        print("[OK] discord.py installed")

    except ImportError:
        errors.append("discord.py not installed — run: pip install -r requirements.txt")

    print()

    for w in warnings:
        print(f"WARN: {w}")

    for e in errors:
        print(f"ERROR: {e}")

    if errors:
        print("\nFix the errors above, then run: python bot.py")
        print("See SETUP.md for full instructions.")
        return 1

    print("\nAll checks passed. Run: python bot.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

