from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import hashlib
from datetime import datetime, timezone
import logging

from . import models, schemas, database, ai, scheduler

router = APIRouter()
logger = logging.getLogger(__name__)

def get_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def enrich_note_background(note_id: int):
    db = database.SessionLocal()
    try:
        note = db.query(models.Note).filter(models.Note.id == note_id).first()
        if not note or not note.content:
            return
            
        current_hash = get_content_hash(note.content)
        if note.content_hash == current_hash and note.ai_summary:
            # Already enriched for this content
            return

        logger.info(f"Enriching note {note_id} in background...")
        result = ai.enrich_note(note.content)
        
        if result:
            note.ai_summary = result.get("summary")
            note.ai_tags = result.get("tags", [])
            
            # Handle due date parsing
            due_date_str = result.get("due_date")
            if due_date_str:
                try:
                    # Basic ISO parsing
                    note.due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Failed to parse due_date: {due_date_str}")
            
            note.priority = result.get("priority")
            note.content_hash = current_hash
            note.ai_updated_at = datetime.utcnow()
            
            db.commit()
            
            if note.due_date:
                scheduler.schedule_reminder(note.id, note.due_date)
                
    except Exception as e:
        logger.error(f"Background enrichment failed for note {note_id}: {e}")
    finally:
        db.close()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/notes", response_model=schemas.NoteResponse)
def create_note(note: schemas.NoteCreate, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    db_note = models.Note(**note.model_dump())
    if db_note.due_date:
        # Ensure it's stored timezone naive or utc as appropriate, sqlite handles naive as utc usually
        pass
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    
    background_tasks.add_task(enrich_note_background, db_note.id)
    
    if db_note.due_date:
        scheduler.schedule_reminder(db_note.id, db_note.due_date)
        
    return db_note

@router.get("/notes", response_model=List[schemas.NoteResponse])
def get_notes(
    q: Optional[str] = None, 
    tag: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Note)
    if q:
        search = f"%{q}%"
        # Since tags and ai_tags are JSON strings in SQLite, we can just LIKE them
        query = query.filter(
            or_(
                models.Note.title.ilike(search),
                models.Note.content.ilike(search),
                models.Note.ai_summary.ilike(search),
                models.Note.tags.ilike(search),
                models.Note.ai_tags.ilike(search)
            )
        )
    
    if tag:
        tag_search = f"%\"{tag}\"%"
        query = query.filter(
            or_(
                models.Note.tags.ilike(tag_search),
                models.Note.ai_tags.ilike(tag_search)
            )
        )
        
    return query.order_by(models.Note.updated_at.desc()).all()

@router.get("/notes/{note_id}", response_model=schemas.NoteResponse)
def get_note(note_id: int, db: Session = Depends(database.get_db)):
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.put("/notes/{note_id}", response_model=schemas.NoteResponse)
def update_note(note_id: int, note_update: schemas.NoteUpdate, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    update_data = note_update.model_dump(exclude_unset=True)
    content_changed = False
    
    if "content" in update_data and update_data["content"] != db_note.content:
        content_changed = True
        
    for key, value in update_data.items():
        setattr(db_note, key, value)
        
    db_note.reminder_fired = False # Reset if updated
    db.commit()
    db.refresh(db_note)
    
    if content_changed:
        background_tasks.add_task(enrich_note_background, db_note.id)
        
    if db_note.due_date:
        scheduler.schedule_reminder(db_note.id, db_note.due_date)
    else:
        scheduler.remove_reminder(db_note.id)
        
    return db_note

@router.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(database.get_db)):
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    db.delete(db_note)
    db.commit()
    scheduler.remove_reminder(note_id)
    return {"status": "deleted"}

@router.post("/notes/{note_id}/enrich", response_model=schemas.NoteResponse)
def force_enrich_note(note_id: int, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    """Force re-enrichment of a note by clearing cached AI data."""
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Clear cached AI data so background task re-runs
    db_note.content_hash = None
    db_note.ai_summary = None
    db_note.ai_tags = None
    db_note.priority = None
    db_note.ai_updated_at = None
    db.commit()
    db.refresh(db_note)
    
    background_tasks.add_task(enrich_note_background, db_note.id)
    return db_note

@router.post("/ask", response_model=schemas.AskResponse)
def ask_question(request: schemas.AskRequest, db: Session = Depends(database.get_db)):
    notes = db.query(models.Note).order_by(models.Note.updated_at.desc()).limit(30).all()
    notes_list = [
        {"id": n.id, "title": n.title, "content": n.content}
        for n in notes
    ]
    
    result = ai.answer_question(request.question, notes_list)
    return result

@router.get("/reminders/due")
def get_due_reminders(db: Session = Depends(database.get_db)):
    # Returns notes where reminder_fired is True
    notes = db.query(models.Note).filter(models.Note.reminder_fired == True).all()
    result = [{"id": n.id, "title": n.title, "due_date": n.due_date} for n in notes]
    
    # Once fetched, reset them so they don't fire again
    for n in notes:
        n.reminder_fired = False
    if notes:
        db.commit()
        
    return {"reminders": result}
