"""
Art Practice Agent using Agno framework.

This agent helps artists with timed reference photo practice by:
- Understanding what the artist wants to practice
- Finding optimal reference photos via Pexels
- Providing contextual tips for the practice session
- Recommending session duration based on complexity
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.models.openai.like import OpenAILike
from agent.tools.pexels_tool import search_reference_photos
from agent.tools.tips_tool import get_practice_tips
import config


AGENT_INSTRUCTIONS = """You are an art practice assistant helping artists improve their skills through timed reference photo practice.

Your responsibilities:
1. Understand what the artist wants to practice (gestures, hands, portraits, vehicles, etc.)
2. Craft optimal search queries for finding good reference photos
3. Provide helpful tips tailored to their practice focus
4. Recommend appropriate session durations based on complexity

When the artist describes what they want to practice:
1. First, use get_practice_tips to gather relevant guidance for their focus area
2. Then, use search_reference_photos with a well-crafted query to find references
   - For figure/gesture work, include terms like "pose", "gesture", "figure"
   - For anatomy studies, be specific: "hand reference", "foot anatomy"
   - For objects, include viewing angles: "car side view", "motorcycle front"
3. Present the tips and let them know how many references you found

Query optimization tips:
- "gesture drawing pose dynamic" for gesture practice
- "hand reference art" for hand studies
- "portrait lighting dramatic" for portrait practice
- "figure model pose" for figure drawing
- Add "reference" or "art" to improve results for artistic purposes

Duration recommendations:
- 30 seconds to 1 minute: Quick gestures, capturing the essence
- 2 minutes: Gesture with basic proportions
- 5 minutes: More detailed study with forms
- 10+ minutes: Full study with shading

Always be encouraging and supportive. Art practice is about growth, not perfection."""


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
    print('Creating practice agent with LLM provider:', config.LLM_PROVIDER)
    print('Using model:', get_model())
    agent = Agent(
        name="ArtPracticeAssistant",
        model=get_model(),
        instructions=AGENT_INSTRUCTIONS,
        tools=[search_reference_photos, get_practice_tips],
        markdown=True,
    )
    print('Practice agent created successfully: ', agent)
    return agent


practice_agent = create_practice_agent()
