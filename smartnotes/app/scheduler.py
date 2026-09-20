from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Use UTC to avoid timezone issues
scheduler = BackgroundScheduler(timezone="UTC")

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

def mark_reminder_fired(note_id: int):
    from .database import SessionLocal
    from .models import Note
    
    db = SessionLocal()
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if note:
            note.reminder_fired = True
            db.commit()
            logger.info(f"Reminder fired for note {note_id}")
    except Exception as e:
        logger.error(f"Error firing reminder for note {note_id}: {e}")
    finally:
        db.close()

def schedule_reminder(note_id: int, due_date: datetime):
    job_id = f"reminder_note_{note_id}"
    
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    if due_date:
        # Ensure timezone awareness if naive
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)
            
        if due_date > datetime.now(timezone.utc):
            scheduler.add_job(
                mark_reminder_fired,
                'date',
                run_date=due_date,
                args=[note_id],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Scheduled reminder for note {note_id} at {due_date}")

def remove_reminder(note_id: int):
    job_id = f"reminder_note_{note_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed reminder for note {note_id}")
