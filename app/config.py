import os
from pathlib import Path

PORT = int(os.getenv("PORT", "8000"))
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DUMP_INTERVAL_SECONDS = int(os.getenv("DUMP_INTERVAL_SECONDS", "300"))
DUMP_FILE = DATA_DIR / "glossary_dump.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

DEFAULT_ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

VALID_DOMAINS = ["法律", "技术", "产品", "营销", "通用", "UI", "财务"]
VALID_PARTS_OF_SPEECH = ["noun", "verb", "adj", "phrase"]
VALID_STATUSES = ["draft", "approved", "deprecated"]
VALID_ROLES = ["translator", "reviewer", "domain_lead", "admin", "readonly"]

RATE_LIMIT_PER_MINUTE = 100
RATE_LIMIT_BATCH_PER_MINUTE = 10

ROLLBACK_WINDOW_DAYS = 30

POINTS_CREATE = 5
POINTS_APPROVED = 10
POINTS_REJECTED = -3
