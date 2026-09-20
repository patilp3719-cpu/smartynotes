import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .database import engine, Base, SessionLocal
from . import routes, models, scheduler
from datetime import datetime, timezone
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartNotes API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api")

@app.on_event("startup")
def startup_event():
    try:
        scheduler.start_scheduler()
        
        # Reload pending reminders from DB
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            notes_with_due = db.query(models.Note).filter(
                models.Note.due_date > now,
                models.Note.reminder_fired == False
            ).all()
            for note in notes_with_due:
                scheduler.schedule_reminder(note.id, note.due_date)
            logger.info(f"Reloaded {len(notes_with_due)} reminders.")
            
            # Auto-seed initial demo notes if DB is empty (e.g. on fresh Vercel /tmp DB)
            note_count = db.query(models.Note).count()
            if note_count == 0:
                demo_notes = [
                    {
                        "title": "Meeting with teammates",
                        "content": "Discussed the new project. We need to focus on local-first AI and fast search. Action items: setup DB, design UI.",
                        "tags": ["work", "meeting"]
                    },
                    {
                        "title": "Grocery List",
                        "content": "- Milk\n- Eggs\n- Bread\n- Coffee beans",
                        "tags": ["task"]
                    },
                    {
                        "title": "Project Deadline",
                        "content": "Submit the hackathon project before Sunday 5PM EST. Make sure the demo video is uploaded.",
                        "tags": ["important note", "plan"],
                        "due_date": datetime.utcnow()
                    }
                ]
                for n_data in demo_notes:
                    db.add(models.Note(**n_data))
                db.commit()
                logger.info("Auto-seeded initial demo notes.")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Scheduler could not start (normal in some serverless environments): {e}")

from pathlib import Path

# Mount static files (this must be after API routes so /api is not shadowed)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
else:
    logger.warning(f"Static directory not found at {static_dir}. Frontend will not be served.")
