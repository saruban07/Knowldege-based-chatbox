# Sample Data — Inputs and Expected Outputs

This folder contains sample inputs used during development and testing, and their expected outputs from the bot.

---

## Sample Input 1 — Direct KB Question

**Input (typed in Discord):**
```
How do I reset my password?
```

**Expected Output:**
```
To reset your password:
1. Go to the login page and click Forgot Password.
2. Enter your registered email address.
3. Check your inbox for a reset link (check spam if not received).
4. Click the link and enter a new password.

Sources:
• password-reset.md > Resetting Your Password

Confidence: 91%
```

---

## Sample Input 2 — Alternate Phrasing (Semantic Search)

**Input:**
```
how do I remove my account
```

**Expected Output:**
```
To permanently delete your account:
1. Go to Settings > Account > Danger Zone.
2. Click Delete Account.
3. Type your password to confirm.
4. Click Permanently Delete.
All data will be removed within 30 days per our data retention policy.

Sources:
• account-management.md > Deleting Your Account

Confidence: 78%
```

> Note: The KB section is titled "Deleting Your Account" — the query "remove my account" retrieves it correctly via query expansion.

---

## Sample Input 3 — Another Alternate Phrasing

**Input:**
```
I want to cancel my account permanently
```

**Expected Output:**
```
To permanently delete your account:
1. Go to Settings > Account > Danger Zone.
2. Click Delete Account.
3. Type your password to confirm.
4. Click Permanently Delete.

Sources:
• account-management.md > Deleting Your Account

Confidence: 75%
```

---

## Sample Input 4 — Billing Question

**Input:**
```
How do I download my invoice?
```

**Expected Output:**
```
To download an invoice:
1. Go to Billing > Invoice History.
2. Click the invoice you want to download.
3. Click Download PDF.

Sources:
• billing.md > Invoice History

Confidence: 88%
```

---

## Sample Input 5 — Low Confidence Escalation

**Input:**
```
What is the capital of France?
```

**Expected Output:**
```
I couldn't confidently answer this from the knowledge base.
Confidence: 0%

Would you like me to create a support ticket? Reply yes to confirm,
or use !ticket <your question>.
```

**Follow-up input:**
```
yes
```

**Expected Output:**
```
Support ticket created.

Ticket #1001
Question: What is the capital of France?
Timestamp: 2026-06-06 15:30:00 UTC
```

---

## Sample Input 6 — Manual Ticket

**Input:**
```
!ticket I cannot access my billing dashboard after the recent update
```

**Expected Output:**
```
Support ticket created.

Ticket #1002
Question: I cannot access my billing dashboard after the recent update
Timestamp: 2026-06-06 15:31:00 UTC
```

---

## Sample Input 7 — !stats Command

**Input:**
```
!stats
```

**Expected Output (Discord embed):**
```
Bot Statistics

KB Files          4
Indexed Chunks    19
Tickets           2
LLM (Groq)        llama-3.3-70b-versatile
Embeddings        all-MiniLM-L6-v2
Confidence Threshold  75%
```

---

## Sample Input 8 — !analytics Command

**Input:**
```
!analytics
```

**Expected Output (Discord embed):**
```
Chatbot Analytics

Total Questions     6
Answered            5
Escalated           1
Average Confidence  83%
Ticket Resolution Rate  0%
Avg Resolution Time     —

Top Questions
how do I reset my password (2)
how do I remove my account (1)
how do I download my invoice (1)
```

---

## Sample Input 9 — !reindex After KB Change

**Input:**
```
!reindex
```

**Expected Output:**
```
Reindex complete.
• KB files: 4
• Indexed chunks: 21
```

---

## Sample tickets/tickets.json (generated output)

```json
{
  "next_id": 1003,
  "tickets": [
    {
      "id": 1001,
      "question": "What is the capital of France?",
      "user_id": "1512627816980549644",
      "username": "sara",
      "channel_id": "123456789",
      "timestamp": "2026-06-06 15:30:00 UTC",
      "status": "open",
      "resolved_at": null,
      "resolved_by": null
    },
    {
      "id": 1002,
      "question": "I cannot access my billing dashboard after the recent update",
      "user_id": "1512627816980549644",
      "username": "sara",
      "channel_id": "123456789",
      "timestamp": "2026-06-06 15:31:00 UTC",
      "status": "open",
      "resolved_at": null,
      "resolved_by": null
    }
  ]
}
```

---

## Sample analytics/analytics.json (generated output)

```json
{
  "total_questions": 6,
  "answered_questions": 5,
  "escalated_questions": 1,
  "confidence_scores": [0.91, 0.78, 0.75, 0.88, 0.0, 0.85],
  "top_questions": {
    "how do I reset my password": 2,
    "how do I remove my account": 1,
    "I want to cancel my account permanently": 1,
    "how do I download my invoice": 1,
    "what is the capital of france": 1
  }
}
```