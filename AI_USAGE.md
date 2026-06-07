# AI Usage Note

**Project:** Discord Knowledge Base Support Bot  
**Team:** Team - 24 

---

## What AI Helped With

| Area | How AI Was Used |
|------|----------------|
| **RAG Pipeline Design** | Claude suggested the three-layer confidence scoring formula combining retrieval similarity (40%), chunk support (25%), and LLM self-reported confidence (35%) |
| **JSON Parsing Bug** | Diagnosed the `Invalid control character` crash in `_parse_llm_json` — Groq was emitting literal newlines inside JSON strings. AI provided the char-by-char sanitizer fix |
| **Retrieval Miss Fix** | Identified that `MIN_SIMILARITY_THRESHOLD = 0.3` was too high for MiniLM paraphrased queries and suggested lowering to `0.20` with query expansion as the solution |
| **Alias-Aware Chunking** | Suggested extracting `Also known as:` blocks from KB sections and prepending them to every sub-chunk so alternate phrasings always travel with content into the vector store |
| **Query Expansion** | Generated the `_EXPANSION_ALIASES` dictionary mapping common support phrasings to canonical KB terms (delete → remove account, cancel, close account etc.) |
| **Prompt Engineering** | Helped write the `SYSTEM_PROMPT` with the JSON-only output constraint and the instruction to use `\n` instead of literal newlines |
| **Documentation** | Generated `README.md`, `SETUP.md`, demo video script, and this file based on the actual codebase |
| **Git Workflow** | Guided branch creation, commit amending after GitHub secret scanning block, and force push recovery |

---

## What AI Got Wrong

| Issue | What Happened | How We Fixed It |
|-------|--------------|-----------------|
| **Duplicate `loader.py`** | AI generated a second `loader.py` as a "fix" that conflicted with the existing one, causing `ImportError: cannot import name 'DocumentChunk'` | Kept the original file, only added the missing alias extraction logic |
| **`prompts.py` assumption** | AI assumed `prompts.py` didn't exist and rewrote `llm.py` to inline the prompts — but the file existed and was already imported | Reverted `llm.py` imports and updated `prompts.py` directly instead |
| **Threshold suggestion** | AI initially suggested `MIN_SIMILARITY_THRESHOLD = 0.25` — still caused occasional misses on short queries | Tested empirically and settled on `0.20` |
| **Over-engineering** | AI proposed DM-based admin notifications with Discord UI buttons before understanding the scope — features were not needed at this stage | Scoped down to `!tickets` and `!resolve` commands only, then further simplified to `!analytics` only per actual requirements |

---

## Best Prompts Used

**1. Diagnosing the retrieval miss**
> "The bot answers 'how to update my profile' correctly but says it's out of context for 'how to delete my account'. Both sections exist in the same KB file. Check embeddings.py, retriever.py, and the KB markdown structure."

**2. Fixing the JSON crash**
> "Groq API call returns HTTP 200 but throws `Invalid control character at: line 2 column 58`. Here is the raw LLM response and my `_parse_llm_json` function. Fix the parser without changing the rest of llm.py."

**3. Scoped file update**
> "This is my existing bot.py. I only want to add `!analytics` and admin ticket viewing. Do not change anything else — paste only the lines that change and tell me exactly where to put them."

**4. Documentation generation**
> "Generate a README.md for this project. It must include: setup instructions, run instructions, architecture overview with ASCII flow diagram, and assumptions and limitations. Base it only on the actual files I have shared — do not invent features."

**5. Git recovery**
> "GitHub rejected my push with GH013 secret scanning violation. The secret is in `.env.example` inside commit `60c7bd6`. I cannot rewrite history freely because teammates have cloned the repo. Give me the exact commands to fix and re-push."

---

## Summary

AI was used as a **pair programmer and debugger** throughout development — not to generate the project from scratch, but to diagnose specific bugs, suggest targeted fixes, and accelerate documentation. Every AI suggestion was reviewed, tested, and in several cases corrected before being committed.
