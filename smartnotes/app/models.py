from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
import datetime
from .database import Base

class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, default="Untitled")
    content = Column(Text, default="")
    tags = Column(JSON, default=list) # JSON list
    ai_summary = Column(Text, nullable=True)
    ai_tags = Column(JSON, nullable=True) # JSON list
    due_date = Column(DateTime, nullable=True)
    priority = Column(String(50), nullable=True)
    content_hash = Column(String, nullable=True)
    reminder_fired = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    ai_updated_at = Column(DateTime, nullable=True)
