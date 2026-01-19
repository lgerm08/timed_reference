"""
Tips Generator Subagent.

Generates intelligent practice tips for art practice sessions.
Tips are displayed in a separate panel, not in the main chat.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.models.openai.like import OpenAILike
import config


TIPS_INSTRUCTIONS = """You are an art practice coach helping artists improve their skills.

Your job is to provide practice tips in a structured format for TIMED REFERENCE drawing.

## YOUR OUTPUT FORMAT

Return a JSON object with these fields:
- practice_focus: string - what they're practicing (e.g., "Hand Studies")
- duration_advice: string - advice based on the time per image
- focus_areas: list of 3-4 strings - what to pay attention to
- common_mistakes: list of 2-3 strings - mistakes to avoid
- warm_up_suggestion: string - a quick warm-up exercise

## DURATION GUIDELINES

- 30 seconds: Pure gesture, line of action only, no details
- 1 minute: Gesture + basic shapes, find the rhythm
- 2 minutes: Gesture + forms + basic proportions
- 5 minutes: Full study with forms, proportions, some details
- 10 minutes: Complete study with shading and refinement

## EXAMPLE OUTPUT

For "hands" at 2 minutes per image:
{
  "practice_focus": "Hand Studies",
  "duration_advice": "At 2 minutes, capture the gesture first, then block in the palm and finger cylinders. Skip fine details.",
  "focus_areas": [
    "Start with the overall gesture/action of the hand",
    "Block in the palm as a simple box shape",
    "Notice how fingers overlap and foreshorten",
    "Pay attention to the thumb's unique angle"
  ],
  "common_mistakes": [
    "Drawing fingers as separate elements instead of connected to the palm",
    "Making all fingers the same length",
    "Forgetting to show the hand's thickness"
  ],
  "warm_up_suggestion": "Draw 5 quick hand silhouettes in 30 seconds each to loosen up"
}

Be specific and practical. No generic advice like "practice more" - give actionable guidance.
"""


# Tips cache to avoid regenerating for same themes
_tips_cache: dict[str, dict] = {}


def get_tips_model():
    """Get a fast/cheap model for tips generation."""
    provider = config.LLM_PROVIDER.lower()

    # Use faster models for tips - they don't need heavy reasoning
    if provider == "groq":
        return Groq(
            id="llama-3.1-8b-instant",  # Fast model
            api_key=config.GROQ_API_KEY,
        )
    elif provider == "moonshot":
        return OpenAILike(
            id=config.MOONSHOT_MODEL,
            api_key=config.MOONSHOT_API_KEY,
            base_url="https://api.moonshot.ai/v1",
        )
    elif provider == "openai":
        return OpenAIChat(
            id="gpt-4o-mini",  # Cheaper/faster model
            api_key=config.OPENAI_API_KEY,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def create_tips_agent() -> Agent:
    """Create the tips generator subagent."""
    return Agent(
        name="TipsGenerator",
        model=get_tips_model(),
        instructions=TIPS_INSTRUCTIONS,
        markdown=True,
    )


# Singleton instance
_tips_agent: Agent | None = None


def get_tips_agent() -> Agent:
    """Get or create the tips agent singleton."""
    global _tips_agent
    if _tips_agent is None:
        _tips_agent = create_tips_agent()
    return _tips_agent


def generate_practice_tips(practice_focus: str, duration_seconds: int = 60) -> dict:
    """
    Generate practice tips using the subagent.

    Args:
        practice_focus: What the artist wants to practice (e.g., "hands", "gestures")
        duration_seconds: Seconds per image

    Returns:
        Dict with tips structure
    """
    import json

    # Check cache first
    cache_key = f"{practice_focus.lower()}_{duration_seconds}"
    if cache_key in _tips_cache:
        print(f"[TIPS] Cache hit for '{cache_key}'")
        return _tips_cache[cache_key]

    duration_minutes = duration_seconds // 60 if duration_seconds >= 60 else duration_seconds / 60

    # Build prompt
    prompt = f"""Generate practice tips for:
- Subject: {practice_focus}
- Duration per image: {duration_seconds} seconds ({duration_minutes} minutes)

Return ONLY the JSON object, no other text."""

    print(f"[TIPS] Generating tips for '{practice_focus}' at {duration_seconds}s")

    try:
        agent = get_tips_agent()
        response = agent.run(prompt)

        # Parse the response
        content = response.content if response.content else ""

        # Try to extract JSON from the response
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()

        tips = json.loads(content)

        # Ensure required fields
        if "practice_focus" not in tips:
            tips["practice_focus"] = practice_focus
        if "duration_minutes" not in tips:
            tips["duration_minutes"] = duration_minutes

        # Cache the result
        _tips_cache[cache_key] = tips

        print(f"[TIPS] Generated tips successfully")
        return tips

    except json.JSONDecodeError as e:
        print(f"[TIPS] Failed to parse tips JSON: {e}")
        return _get_fallback_tips(practice_focus, duration_seconds)
    except Exception as e:
        print(f"[TIPS] Error generating tips: {e}")
        return _get_fallback_tips(practice_focus, duration_seconds)


def _get_fallback_tips(practice_focus: str, duration_seconds: int) -> dict:
    """Return fallback tips when generation fails."""
    duration_minutes = duration_seconds // 60 if duration_seconds >= 60 else duration_seconds / 60

    if duration_seconds <= 30:
        duration_advice = "Focus only on gesture and line of action. No details!"
    elif duration_seconds <= 60:
        duration_advice = "Capture gesture first, then block in major shapes."
    elif duration_seconds <= 120:
        duration_advice = "You have time for gesture, forms, and basic proportions."
    elif duration_seconds <= 300:
        duration_advice = "Include gesture, forms, proportions, and key details."
    else:
        duration_advice = "Full study: gesture, forms, proportions, details, and shading."

    return {
        "practice_focus": practice_focus.title(),
        "duration_minutes": duration_minutes,
        "duration_advice": duration_advice,
        "focus_areas": [
            "Start with the biggest shapes first",
            "Look for the overall gesture or flow",
            "Compare proportions frequently",
            "Step back and check your work",
        ],
        "common_mistakes": [
            "Adding details too early",
            "Not checking proportions",
            "Rushing through the observation phase",
        ],
        "warm_up_suggestion": f"Do quick thumbnail sketches of {practice_focus} to warm up",
    }


def clear_tips_cache():
    """Clear the tips cache."""
    global _tips_cache
    _tips_cache = {}


# Type alias
TipsGenerator = Agent
