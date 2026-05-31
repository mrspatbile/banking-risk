# src/banking_risk/config.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
DATA_DIR      = PROJECT_ROOT / "data"
CACHE_DIR     = DATA_DIR / "cache"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR      = PROJECT_ROOT / "logs"

FRED_API_KEY  = os.getenv("FRED_API_KEY", "")

for _d in [CACHE_DIR, PROCESSED_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)