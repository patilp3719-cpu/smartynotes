import sys
from pathlib import Path

# Add paths so Python can import the app
current_dir = Path(__file__).resolve().parent
smartnotes_dir = current_dir / "smartnotes"

for directory in [str(smartnotes_dir), str(current_dir)]:
    if directory not in sys.path:
        sys.path.insert(0, directory)

from app.main import app
