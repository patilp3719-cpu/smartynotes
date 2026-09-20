import sys
from pathlib import Path

# Add project root and smartnotes directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
smartnotes_dir = root_dir / "smartnotes"

for path in [str(smartnotes_dir), str(root_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from app.main import app
