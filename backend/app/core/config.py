import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present so secrets can be provided via env vars without code changes
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
	load_dotenv(_env_path)

CODEFORCES_API_BASE = "https://codeforces.com/api"
CACHE_TTL_SECONDS = 300
HTTP_TIMEOUT_SECONDS = 15.0

# Database (MySQL) configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "codeforces")

# AWS SES configuration for email notifications
AWS_SES_REGION = os.getenv("AWS_SES_REGION", "us-east-1")
AWS_SES_SENDER = os.getenv("AWS_SES_SENDER", "")
