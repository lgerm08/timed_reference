"""
Art Practice Agent using Agno framework.

This agent helps artists with timed reference photo practice by:
- Understanding what the artist wants to practice
- Finding optimal reference photos via Pexels
- Allowing user to approve images before sessions
- Controlling session parameters (time, image count)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.models.openai.like import OpenAILike
from agent.tools.pinterest_curator_tool import curate_pinterest_images, curate_pinterest_diverse
from agent.tools.session_control_tool import (
    set_session_duration,
    set_image_count,
    get_session_config,
    prepare_session_preview,
    start_practice_session,
)
import config

# Logging setup for Pinterest tracking
import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
pinterest_logger = logging.getLogger('Pinterest')


AGENT_INSTRUCTIONS = """You are an art practice assistant for timed reference drawing sessions.

## IMAGE SOURCE

You use Pinterest for high-quality art references:
- **curate_pinterest_images(theme, count)** - Primary tool for finding reference images
- **curate_pinterest_diverse(queries, per_query)** - Use for variety across multiple aspects

Pinterest provides excellent art-focused content created by and for artists.

Note: If Pinterest is unavailable, the system automatically falls back to Pexels.
You do NOT need to handle this fallback - it happens transparently.

## CRITICAL: BE ACTION-ORIENTED

When the user describes what they want to practice, IMMEDIATELY:
1. Set duration and image count (use smart defaults if not specified)
2. Search for images using Pinterest
3. Prepare preview

DO NOT ask multiple clarifying questions. Use these DEFAULTS:
- Duration: 60 seconds (1 minute) for most subjects
- Duration: 120 seconds (2 minutes) for complex subjects (hands, portraits)
- Image count: 10 images

## WORKFLOW - DO THIS IN ONE TURN

When user says what they want to practice (e.g., "I want to practice hands"):

```
1. set_session_duration(120)  # 2 min for hands
2. set_image_count(10)
3. curate_pinterest_images("hands", count=10)
4. prepare_session_preview()
```

Then tell them: "I found X hand references ready for 2-minute studies. The previews are loading below. Say **start** when ready, or ask for different images."

## FRESH/NEW PHOTOS

When user asks for "fresh", "new", "different", or "haven't seen":
- Just search again with curate_pinterest_images
- Example: `curate_pinterest_images("vintage style model", count=10)`

## STARTING THE SESSION

When user says "start", "begin", "let's go", "ready":
- Call `start_practice_session(theme="the theme")`

## CHANGING SETTINGS

If user wants to adjust BEFORE starting:
- "Make it 5 minutes" → `set_session_duration(300)`
- "Just 5 images" → `set_image_count(5)`
- "Different images" → `curate_pinterest_images(theme, count=N)` then `prepare_session_preview()`

## DURATION GUIDE

- 30s: Quick gesture
- 60s: Gesture + shapes (DEFAULT)
- 120s: Study with proportions (hands, faces)
- 300s: Detailed study
- 600s: Full study with shading

## EXAMPLES

**User**: "hands"
**You**: [set_session_duration(120), set_image_count(10), curate_pinterest_images("hands", count=10), prepare_session_preview()]
"Found 10 hand references for 2-minute studies. Previews loading below. Say **start** when ready!"

**User**: "vintage style model, fresh ones"
**You**: [set_session_duration(60), set_image_count(10), curate_pinterest_images("vintage style model", count=10), prepare_session_preview()]
"Found 10 fresh vintage style references. Say **start** or ask for changes!"

**User**: "start"
**You**: [start_practice_session(theme="hands")]
"Starting session! Good luck with your practice!"

**User**: "make it 5 minutes"
**You**: [set_session_duration(300)]
"Updated to 5 minutes per image. Say **start** when ready!"

Be concise. Be helpful. Get them practicing quickly."""


def get_model():
    """Get the configured LLM model based on config settings."""
    provider = config.LLM_PROVIDER.lower()

    if provider == "moonshot":
        print('Using Moonshot LLM Provider')
        print('Model:', config.MOONSHOT_MODEL)
        return OpenAILike(
            id=config.MOONSHOT_MODEL,
            api_key=config.MOONSHOT_API_KEY,
            base_url="https://api.moonshot.ai/v1",
        )
    elif provider == "groq":
        return Groq(
            id=config.GROQ_MODEL,
            api_key=config.GROQ_API_KEY,
        )
    elif provider == "openai":
        return OpenAIChat(
            id=config.OPENAI_MODEL,
            api_key=config.OPENAI_API_KEY,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def create_practice_agent() -> Agent:
    """Create and return the practice agent instance.

    Returns:
        Configured Agno Agent instance
    """
    pinterest_logger.info("Creating Practice Agent with Pinterest MCP support")
    pinterest_logger.info(f"Pinterest credentials: {'Configured' if config.PINTEREST_EMAIL else 'Not configured (will use Pexels fallback)'}")

    return Agent(
        name="ArtPracticeAssistant",
        model=get_model(),
        instructions=AGENT_INSTRUCTIONS,
        tools=[
            # Pinterest MCP tools (Pexels fallback happens automatically in MCP server)
            curate_pinterest_images,
            curate_pinterest_diverse,
            # Session control tools
            set_session_duration,
            set_image_count,
            get_session_config,
            prepare_session_preview,
            start_practice_session,
        ],
        markdown=True,
    )


practice_agent = create_practice_agent()
