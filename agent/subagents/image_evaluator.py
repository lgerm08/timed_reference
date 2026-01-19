"""
Image Evaluator Subagent.

Evaluates whether an image is good for art reference practice
by analyzing its description and considering user history.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.models.openai.like import OpenAILike
import config


EVALUATOR_INSTRUCTIONS = """You evaluate if images are suitable for ART REFERENCE PRACTICE.

For quick sketch/timed drawing practice, good references have:
- Clear subjects (not cluttered)
- Good lighting that shows form
- Interesting poses or compositions
- Clear visibility of the subject

Bad references for practice:
- Logos, icons, text-heavy images
- Screenshots, graphs, diagrams
- Overly edited/filtered photos
- Cluttered scenes where subject is unclear
- Too dark or overexposed

## YOUR TASK

Given an image description (alt text) and the practice theme, return JSON:
{
  "is_good": true/false,
  "reason": "Brief reason (1 sentence)",
  "confidence": 0.0-1.0
}

## EXAMPLES

Theme: "hands", Alt: "Close up of person's hand holding a coffee cup"
{"is_good": true, "reason": "Clear hand pose with good composition", "confidence": 0.9}

Theme: "hands", Alt: "Business logo with hand icon"
{"is_good": false, "reason": "Logo/icon, not a photograph reference", "confidence": 0.95}

Theme: "portraits", Alt: "Woman smiling at camera with natural lighting"
{"is_good": true, "reason": "Clear portrait with good lighting", "confidence": 0.85}

Theme: "dynamic poses", Alt: "Basketball player jumping for slam dunk"
{"is_good": true, "reason": "Dynamic action pose with clear form", "confidence": 0.9}

Be lenient - if unsure, lean towards accepting the image.
Return ONLY the JSON, no other text.
"""


def get_evaluator_model():
    """Get a fast model for image evaluation."""
    provider = config.LLM_PROVIDER.lower()

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


def create_evaluator_agent() -> Agent:
    """Create the image evaluator subagent."""
    return Agent(
        name="ImageEvaluator",
        model=get_evaluator_model(),
        instructions=EVALUATOR_INSTRUCTIONS,
        markdown=True,
    )


# Singleton instance
_evaluator_agent: Agent | None = None


def get_evaluator_agent() -> Agent:
    """Get or create the evaluator agent singleton."""
    global _evaluator_agent
    if _evaluator_agent is None:
        _evaluator_agent = create_evaluator_agent()
    return _evaluator_agent


# Cache for evaluation results (to avoid re-evaluating same images)
_evaluation_cache: dict[str, dict] = {}


def evaluate_image(alt_text: str, theme: str, use_cache: bool = True) -> dict:
    """
    Evaluate if an image is good for art reference practice.

    Args:
        alt_text: Image description/alt text
        theme: What the user is practicing (e.g., "hands", "dynamic poses")
        use_cache: Whether to use cached results

    Returns:
        Dict with is_good (bool), reason (str), confidence (float)
    """
    import json

    # Handle empty alt text - be lenient
    if not alt_text or not alt_text.strip():
        return {
            "is_good": True,
            "reason": "No description available, allowing by default",
            "confidence": 0.5,
        }

    # Check cache
    cache_key = f"{theme.lower()}:{alt_text[:100]}"
    if use_cache and cache_key in _evaluation_cache:
        return _evaluation_cache[cache_key]

    # Quick keyword filter first (saves API calls)
    alt_lower = alt_text.lower()
    bad_keywords = ["logo", "icon", "screenshot", "graph", "chart", "diagram", "banner", "advertisement"]

    for bad in bad_keywords:
        if bad in alt_lower:
            result = {
                "is_good": False,
                "reason": f"Contains '{bad}' - not suitable for reference practice",
                "confidence": 0.95,
            }
            _evaluation_cache[cache_key] = result
            return result

    # Use subagent for uncertain cases
    prompt = f"""Theme: "{theme}"
Alt text: "{alt_text}"

Is this image good for art reference practice? Return JSON only."""

    try:
        agent = get_evaluator_agent()
        response = agent.run(prompt)

        content = response.content if response.content else ""

        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()
        result = json.loads(content)

        # Ensure required fields
        result.setdefault("is_good", True)
        result.setdefault("reason", "Evaluated by AI")
        result.setdefault("confidence", 0.7)

        _evaluation_cache[cache_key] = result
        return result

    except Exception as e:
        print(f"[EVALUATOR] Error: {e}")
        # Be lenient on errors
        return {
            "is_good": True,
            "reason": "Evaluation failed, allowing by default",
            "confidence": 0.5,
        }


def is_good_reference(alt_text: str, theme: str = "") -> bool:
    """
    Simple boolean check if an image is good for reference.

    This is a drop-in replacement for the simple keyword filter,
    now powered by the evaluator subagent.

    Args:
        alt_text: Image description
        theme: Practice theme (optional, helps with context)

    Returns:
        True if image is suitable for reference practice
    """
    result = evaluate_image(alt_text, theme or "general")
    return result.get("is_good", True)


def clear_evaluation_cache():
    """Clear the evaluation cache."""
    global _evaluation_cache
    _evaluation_cache = {}


# Type alias
ImageEvaluator = Agent
