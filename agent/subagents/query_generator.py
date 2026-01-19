"""
Query Generator Subagent.

Uses LLM intelligence to generate optimal Pexels search queries
based on the user's practice theme/request.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.agent import Agent
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.models.openai.like import OpenAILike
import config


QUERY_GENERATOR_INSTRUCTIONS = """You generate optimal search queries for finding reference photos on Pexels.

## YOUR TASK

Given a user's practice theme, generate 4-6 SPECIFIC search queries that will find diverse, relevant reference photos.

## CRITICAL RULES

1. **Be SPECIFIC, not generic**
   - USER INPUT: "vintage cars"
   - BAD: "car" (too broad)
   - GOOD: "Cadillac classic car", "1960s muscle car", "vintage automobile"

2. **Use CONCRETE terms, not abstract concepts**
   - USER INPUT: "vintage style on model"
   - BAD: "style" (abstract)
   - GOOD: "1950s fashion model", "retro pin-up", "vintage fashion", "classic hollywood glamour"

3. **Each query should find DIFFERENT types of images**
   - If user wants "hands", don't just search "hand" 4 times
   - Search: "pianist hands closeup", "rock climbing grip", "sculptor working clay", "sign language gesture"

4. **Queries should be 2-4 words maximum**
   - Pexels works best with short, specific phrases
   - "1950s fashion model" ✓
   - "vintage retro classic 1950s style fashion model photography" ✗

5. **Think about REAL EXAMPLES**
   - "vintage cars" → Think: Cadillac, Mustang, VW Beetle, classic car show
   - "dynamic poses" → Think: dancer leap, basketball dunk, martial arts kick, gymnast

## OUTPUT FORMAT

Return ONLY a JSON array of query strings:
["query1", "query2", "query3", "query4"]

## EXAMPLES

User: "vintage style on model"
["1950s fashion photography", "retro pin-up model", "classic hollywood portrait", "vintage dress photoshoot"]

User: "hands doing things"
["pianist hands closeup", "pottery making hands", "rock climbing grip", "chef cooking hands"]

User: "vintage cars"
["classic Cadillac car", "1960s Mustang", "vintage VW beetle", "antique car show"]

User: "dynamic action poses"
["ballet dancer leap", "basketball slam dunk", "martial arts kick", "parkour jump"]

User: "angry expressions"
["man shouting angry", "furious woman portrait", "intense stare closeup", "rage expression face"]

Return ONLY the JSON array, no other text.
"""


def get_query_model():
    """Get a fast model for query generation."""
    provider = config.LLM_PROVIDER.lower()

    if provider == "groq":
        return Groq(
            id="llama-3.1-8b-instant",
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
            id="gpt-4o-mini",
            api_key=config.OPENAI_API_KEY,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def create_query_agent() -> Agent:
    """Create the query generator subagent."""
    return Agent(
        name="QueryGenerator",
        model=get_query_model(),
        instructions=QUERY_GENERATOR_INSTRUCTIONS,
        markdown=True,
    )


# Singleton instance
_query_agent: Agent | None = None


def get_query_agent() -> Agent:
    """Get or create the query agent singleton."""
    global _query_agent
    if _query_agent is None:
        _query_agent = create_query_agent()
    return _query_agent


# Cache for generated queries
_query_cache: dict[str, list[str]] = {}


def generate_smart_queries(theme: str, use_cache: bool = True) -> list[str]:
    """
    Generate intelligent search queries for a theme using LLM.

    Args:
        theme: The user's practice theme/request
        use_cache: Whether to use cached results

    Returns:
        List of 4-6 specific search queries
    """
    theme_lower = theme.lower().strip()

    # Check cache
    if use_cache and theme_lower in _query_cache:
        print(f"[QUERY_GEN] Cache hit for '{theme}'")
        return _query_cache[theme_lower]

    prompt = f'Generate search queries for: "{theme}"'

    print(f"[QUERY_GEN] Generating queries for '{theme}'")

    try:
        agent = get_query_agent()
        response = agent.run(prompt)

        content = response.content if response.content else ""

        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()

        # Find the JSON array in the content
        start = content.find('[')
        end = content.rfind(']') + 1
        if start >= 0 and end > start:
            content = content[start:end]

        queries = json.loads(content)

        if isinstance(queries, list) and len(queries) >= 2:
            # Ensure queries are strings and not too long
            queries = [str(q)[:50] for q in queries if q][:6]
            print(f"[QUERY_GEN] Generated: {queries}")

            # Cache the result
            _query_cache[theme_lower] = queries
            return queries

    except Exception as e:
        print(f"[QUERY_GEN] Error: {e}")

    # Fallback: return the theme itself
    print(f"[QUERY_GEN] Fallback to theme as query")
    return [theme]


def clear_query_cache():
    """Clear the query cache."""
    global _query_cache
    _query_cache = {}


# Type alias
QueryGenerator = Agent
