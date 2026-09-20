import os
import json
import logging
from typing import Dict, Any, List
from .prompts import ENRICH_NOTE_PROMPT, ASK_NOTES_PROMPT

logger = logging.getLogger(__name__)

def _clean_json_output(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def _call_gemini(prompt: str) -> str:
    """Call Google Gemini API. Raises on failure."""
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    client = genai.Client(api_key=api_key)
    model = os.getenv("AI_MODEL") or "gemini-2.0-flash"
    logger.info(f"Calling Gemini model: {model}")
    response = client.models.generate_content(model=model, contents=prompt)
    logger.info(f"Gemini response received ({len(response.text)} chars)")
    return response.text

def _call_openai(prompt: str) -> str:
    """Call OpenAI API. Raises on failure."""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key, timeout=30.0)
    model = os.getenv("AI_MODEL") or "gpt-4o-mini"
    logger.info(f"Calling OpenAI model: {model}")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content
    logger.info(f"OpenAI response received ({len(result)} chars)")
    return result

def _mock_llm_response(prompt: str) -> str:
    prompt_lower = prompt.lower()
    if "extract:" in prompt_lower or "extract\n" in prompt_lower:
        return '{"summary": "This is a mock summary.", "tags": ["mock", "test"], "due_date": null, "priority": "medium"}'
    elif "answering questions" in prompt_lower:
        return '{"answer": "This is a mock answer based on your notes.", "source_note_ids": [1]}'
    return "{}"

def _call_llm(prompt: str) -> str:
    """Call the configured AI provider. Falls back: primary -> secondary -> mock."""
    provider = os.getenv("AI_PROVIDER", "mock").lower()
    logger.info(f"AI Provider: {provider}")
    
    if provider == "mock":
        return _mock_llm_response(prompt)
    
    # Build a fallback chain
    providers = []
    if provider == "gemini":
        providers = [("gemini", _call_gemini), ("openai", _call_openai)]
    elif provider == "openai":
        providers = [("openai", _call_openai), ("gemini", _call_gemini)]
    else:
        providers = [("gemini", _call_gemini), ("openai", _call_openai)]
    
    for name, call_fn in providers:
        try:
            return call_fn(prompt)
        except Exception as e:
            logger.error(f"{name} API call failed: {e}")
            continue
    
    logger.warning("All AI providers failed, falling back to mock")
    return _mock_llm_response(prompt)

def enrich_note(content: str) -> Dict[str, Any]:
    if not content.strip():
        return {}
    
    prompt = ENRICH_NOTE_PROMPT.format(content=content)
    try:
        response_text = _call_llm(prompt)
        cleaned_text = _clean_json_output(response_text)
        return json.loads(cleaned_text)
    except Exception as e:
        logger.error(f"Error enriching note: {e}")
        return {}

def answer_question(question: str, notes_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    notes_text = ""
    for note in notes_list:
        notes_text += f"ID: {note['id']}\nTitle: {note['title']}\nContent: {note['content']}\n\n"
    
    prompt = ASK_NOTES_PROMPT.format(question=question, notes=notes_text)
    try:
        response_text = _call_llm(prompt)
        cleaned_text = _clean_json_output(response_text)
        return json.loads(cleaned_text)
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        return {"answer": "Sorry, I encountered an error answering your question.", "source_note_ids": []}
