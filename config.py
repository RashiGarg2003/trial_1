"""Central configuration (loaded from environment / .env)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "northwind_sales.db"))
MAX_SQL_RETRIES = int(os.getenv("MAX_SQL_RETRIES", "3"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "500"))
OUTPUT_DIR = BASE_DIR / "outputs"
