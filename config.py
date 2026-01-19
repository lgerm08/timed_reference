import os
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# Pinterest Configuration (for MCP server with py3-pinterest)
PINTEREST_EMAIL = os.getenv("PINTEREST_EMAIL", "")
PINTEREST_PASSWORD = os.getenv("PINTEREST_PASSWORD", "")

# LLM Provider Configuration
# Supports: "moonshot", "groq", "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "moonshot")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Moonshot Configuration
MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY", "")
MOONSHOT_MODEL = os.getenv("MOONSHOT_MODEL", "kimi-k2-turbo-preview")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

PEXELS_BASE_URL = "https://api.pexels.com/v1"

DEFAULT_TIMER_MINUTES = 1
DEFAULT_PHOTOS_COUNT = 10

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")

# SQLite Configuration for Image Curation Memory
# Database file stored in project directory for portability (no server needed)
SQLITE_DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "timed_reference.db")
)

# Session and History Settings
SESSION_HISTORY_DAYS = int(os.getenv("SESSION_HISTORY_DAYS", "30"))
EXCLUDE_RECENT_IMAGES_DAYS = int(os.getenv("EXCLUDE_RECENT_IMAGES_DAYS", "3"))

# Image Scoring Settings
NEGATIVE_FEEDBACK_DECAY = float(os.getenv("NEGATIVE_FEEDBACK_DECAY", "0.8"))
POSITIVE_FEEDBACK_BOOST = float(os.getenv("POSITIVE_FEEDBACK_BOOST", "1.2"))
FRESHNESS_BONUS = float(os.getenv("FRESHNESS_BONUS", "0.1"))

# Token Optimization Settings
USE_MINIMAL_PROMPTS = os.getenv("USE_MINIMAL_PROMPTS", "false").lower() == "true"
CACHE_AGENT_RESPONSES = os.getenv("CACHE_AGENT_RESPONSES", "true").lower() == "true"
