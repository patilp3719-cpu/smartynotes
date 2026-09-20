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
    finally:
        db.close()

# Mount static files (this must be after API routes so /api is not shadowed)
# In production, check if static folder exists
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
else:
    logger.warning("Static directory not found. Frontend will not be served.")
