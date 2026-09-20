import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models import Note
from datetime import datetime, timedelta, timezone

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

notes_data = [
    {
        "title": "Meeting with John",
        "content": "Discussed the new SmartNotes project. We need to focus on local-first AI and fast search. Action items: setup DB, design UI.",
        "tags": ["work", "meeting"]
    },
    {
        "title": "Grocery List",
        "content": "- Milk\n- Eggs\n- Bread\n- Coffee beans",
        "tags": ["personal"]
    },
    {
        "title": "Project Deadline",
        "content": "Submit the hackathon project before Sunday 5PM EST. Make sure the demo video is uploaded.",
        "tags": ["hackathon", "important"],
        "due_date": datetime.now(timezone.utc) + timedelta(days=2)
    },
    {
        "title": "Python Itertools",
        "content": "itertools.groupby requires the input iterable to be sorted by the grouping key first! Learned this the hard way today.",
        "tags": ["programming", "python", "til"]
    },
    {
        "title": "Idea: AI Agent for scheduling",
        "content": "What if we build an agent that reads email and automatically schedules meetings using the calendar API?",
        "tags": ["ideas", "startup"]
    }
]

for n in notes_data:
    note = Note(**n)
    db.add(note)

db.commit()
db.close()
print("Seeded database with 5 notes.")
