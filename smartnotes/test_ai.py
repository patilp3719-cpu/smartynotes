import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app.ai import _call_llm

try:
    print(_call_llm("test"))
except Exception as e:
    print("ERROR:", e)
