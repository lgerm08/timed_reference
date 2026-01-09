import os
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

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
