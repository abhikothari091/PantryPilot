import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

DB_URL = os.getenv("DATABASE_URL")
RAW_PATH = DATA_DIR / "raw"
PROCESSED_PATH = DATA_DIR / "processed"
ALERT_PATH = DATA_DIR / "alerts"
