ENRICH_NOTE_PROMPT = """You are an AI assistant for a smart notepad.
Read the following note and extract:
1. A summary (maximum 2 sentences).
2. Suggested tags (maximum 5, all lowercase). Prefer these tags if applicable: "task", "plan", "idea", "important note".
3. A due_date (ISO-8601 string) if there is an explicit deadline mentioned. If not, return null.
4. Priority ("low", "medium", or "high") based on the content's urgency and importance.

Return ONLY strict JSON matching this schema, without markdown code fences or any other text:
{{
  "summary": "...",
  "tags": ["tag1", "tag2"],
  "due_date": "YYYY-MM-DDTHH:MM:SS", // or null
  "priority": "low" // or "medium", "high"
}}

Note content:
{content}
"""

ASK_NOTES_PROMPT = """You are an AI assistant answering questions based on the user's notes.
Use ONLY the provided notes to answer the question. If the answer is not in the notes, say "I cannot find the answer in your notes."
Along with the answer, provide the IDs of the source notes used to construct the answer.

Return ONLY strict JSON matching this schema, without markdown code fences or any other text:
{{
  "answer": "...",
  "source_note_ids": [1, 2]
}}

Notes:
{notes}

Question:
{question}
"""
