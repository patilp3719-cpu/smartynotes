from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class NoteBase(BaseModel):
    title: Optional[str] = Field(default="Untitled", max_length=255)
    content: Optional[str] = Field(default="")
    tags: Optional[List[str]] = Field(default_factory=list)
    due_date: Optional[datetime] = None

class NoteCreate(NoteBase):
    pass

class NoteUpdate(NoteBase):
    pass

class NoteResponse(NoteBase):
    id: int
    ai_summary: Optional[str] = None
    ai_tags: Optional[List[str]] = None
    priority: Optional[str] = None
    content_hash: Optional[str] = None
    reminder_fired: bool = False
    created_at: datetime
    updated_at: datetime
    ai_updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    source_note_ids: List[int]
