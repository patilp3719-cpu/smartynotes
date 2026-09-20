import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
from app.ai import _clean_json_output

client = TestClient(app)

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

def test_create_and_get_note():
    res = client.post("/api/notes", json={"title": "Test Note", "content": "This is a test"})
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Test Note"
    note_id = data["id"]
    
    res2 = client.get(f"/api/notes/{note_id}")
    assert res2.status_code == 200
    assert res2.json()["title"] == "Test Note"

def test_search_notes():
    # Make sure we have the note first
    client.post("/api/notes", json={"title": "SearchTarget", "content": "UniqueContent123"})
    
    res = client.get("/api/notes?q=UniqueContent123")
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert res.json()[0]["title"] == "SearchTarget"

def test_json_cleaner():
    raw_markdown = "```json\n{\"test\": 1, \"list\": [1,2]}\n```"
    cleaned = _clean_json_output(raw_markdown)
    parsed = json.loads(cleaned)
    assert parsed["test"] == 1
    assert parsed["list"] == [1, 2]
    
    raw_plain = "{\"test\": 2}"
    cleaned = _clean_json_output(raw_plain)
    parsed = json.loads(cleaned)
    assert parsed["test"] == 2
