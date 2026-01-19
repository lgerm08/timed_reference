"""
Enhanced Query Generator with Pinterest-optimized strategies.

This improved version generates better queries for art reference images by:
1. Using artistic terminology
2. Considering composition variety
3. Adding visual diversity keywords
4. Optimizing for Pinterest's search patterns
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


ENHANCED_QUERY_INSTRUCTIONS = """You generate EXPERT-LEVEL search queries for finding ART REFERENCE photos.

## YOUR EXPERTISE

You understand:
- Artistic terminology (contrapposto, foreshortening, chiaroscuro, etc.)
- Composition theory (rule of thirds, golden ratio, leading lines)
- Visual diversity (angles, lighting, perspectives)
- Pinterest's rich art reference ecosystem

## YOUR TASK

Generate 4-6 queries that find DIVERSE, HIGH-QUALITY art references.

## CRITICAL IMPROVEMENTS OVER BASIC SEARCH

### 1. USE ARTISTIC TERMINOLOGY
- BAD: "person standing"
- GOOD: "contrapposto pose figure", "gesture drawing model"

### 2. SPECIFY VISUAL CHARACTERISTICS
- BAD: "hand"
- GOOD: "hand anatomy study", "foreshortened hand reference", "hand gesture various angles"

### 3. CONSIDER COMPOSITION & ANGLE DIVERSITY
- If searching "portraits", vary: "portrait three-quarter view", "profile silhouette portrait", "portrait dramatic lighting"
- If searching "animals", vary: "cat anatomy side view", "cat dynamic leap", "cat curled sleeping"

### 4. LEVERAGE PINTEREST PATTERNS
Pinterest excels at:
- Art references and studies
- Tutorial and process images
- Curated aesthetic collections
- Multiple angles of same subject

Good Pinterest queries: "figure drawing reference", "anatomy study reference", "lighting reference for artists"

### 5. EACH QUERY MUST FIND DIFFERENT IMAGES
Don't repeat similar queries. Each should explore different:
- Angles (front, side, 3/4, top-down, low-angle)
- Lighting (dramatic, soft, backlit, rim light)
- Context (studio, nature, action, static)
- Composition (closeup, wide, cropped, full-body)

## EXAMPLES WITH EXPLANATIONS

User: "hands"
[
  "hand anatomy reference sketch",     // study focus
  "hands holding object various",      // functional context
  "foreshortened hand reaching",       // perspective challenge
  "expressive hand gesture"            // emotional aspect
]

User: "dynamic poses"
[
  "figure gesture 30 second sketch",   // quick gesture reference
  "contrapposto standing pose",        // classical pose
  "action pose extreme foreshortening", // perspective challenge
  "dynamic movement reference photo"    // motion capture
]

User: "vintage cars"
[
  "classic car three-quarter view",    // standard product angle
  "vintage automobile detail closeup", // texture/detail study
  "retro car dramatic lighting",       // lighting study
  "antique vehicle side profile"       // technical drawing angle
]

User: "portrait lighting"
[
  "Rembrandt lighting portrait",       // specific technique
  "split lighting face reference",     // specific technique
  "butterfly lighting example",        // specific technique
  "dramatic rim light portrait"        // specific technique
]

User: "fantasy character design"
[
  "warrior costume reference",         // costume design
  "medieval armor detail study",       // material/texture
  "fantasy character concept art",     // style inspiration
  "dramatic hero pose reference"       // pose/composition
]

## OUTPUT FORMAT

Return ONLY a JSON array:
["query1", "query2", "query3", "query4"]

No explanations. Just the array.

## QUALITY CHECK

Before returning, verify:
✓ Each query is 2-5 words
✓ Queries use specific artistic or technical terms
✓ Each query will find DIFFERENT types of images
✓ Mix of angles, lighting, contexts represented
✓ Suitable for ART REFERENCE purposes (not generic stock photos)
"""


def get_enhanced_query_model():
    """Get LLM model for enhanced query generation."""
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


def create_enhanced_query_agent() -> Agent:
    """Create the enhanced query generator agent."""
    return Agent(
        name="EnhancedQueryGenerator",
        model=get_enhanced_query_model(),
        instructions=ENHANCED_QUERY_INSTRUCTIONS,
        markdown=True,
    )


# Singleton
_enhanced_query_agent: Agent | None = None


def get_enhanced_query_agent() -> Agent:
    """Get or create the enhanced query agent singleton."""
    global _enhanced_query_agent
    if _enhanced_query_agent is None:
        _enhanced_query_agent = create_enhanced_query_agent()
    return _enhanced_query_agent


# Cache
_enhanced_query_cache: dict[str, list[str]] = {}


def generate_enhanced_queries(
    theme: str,
    use_cache: bool = True,
    pinterest_optimized: bool = True
) -> list[str]:
    """
    Generate enhanced art-focused queries using LLM intelligence.

    Args:
        theme: The user's practice theme/request
        use_cache: Whether to use cached results
        pinterest_optimized: Add Pinterest-specific optimizations

    Returns:
        List of 4-6 expert-level search queries
    """
    theme_lower = theme.lower().strip()

    # Check cache
    if use_cache and theme_lower in _enhanced_query_cache:
        print(f"[Enhanced Query] Cache hit for '{theme}'")
        return _enhanced_query_cache[theme_lower]

    prompt = f'Generate art reference queries for: "{theme}"'

    if pinterest_optimized:
        prompt += ' (Pinterest-optimized with artistic terminology)'

    print(f"[Enhanced Query] Generating for '{theme}'")

    try:
        agent = get_enhanced_query_agent()
        response = agent.run(prompt)

        content = response.content if response.content else ""

        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()

        # Extract JSON array
        start = content.find('[')
        end = content.rfind(']') + 1
        if start >= 0 and end > start:
            content = content[start:end]

        queries = json.loads(content)

        if isinstance(queries, list) and len(queries) >= 2:
            # Validate and clean queries
            queries = [str(q).strip()[:60] for q in queries if q][:6]

            print(f"[Enhanced Query] Generated: {queries}")

            # Cache
            _enhanced_query_cache[theme_lower] = queries
            return queries

    except Exception as e:
        print(f"[Enhanced Query] Error: {e}")
        import traceback
        traceback.print_exc()

    # Fallback
    print(f"[Enhanced Query] Fallback to theme")
    return [f"{theme} reference"]


def clear_enhanced_query_cache():
    """Clear the query cache."""
    global _enhanced_query_cache
    _enhanced_query_cache = {}


# Comparison helper for education
def compare_query_strategies(theme: str):
    """
    Educational function: Compare basic vs enhanced query generation.

    Shows the difference in query quality between basic and enhanced strategies.
    """
    from agent.subagents.query_generator import generate_smart_queries

    print(f"\n{'='*60}")
    print(f"QUERY STRATEGY COMPARISON: '{theme}'")
    print(f"{'='*60}\n")

    print("BASIC STRATEGY (query_generator.py):")
    basic_queries = generate_smart_queries(theme, use_cache=False)
    for i, q in enumerate(basic_queries, 1):
        print(f"  {i}. {q}")

    print("\nENHANCED STRATEGY (enhanced_query_generator.py):")
    enhanced_queries = generate_enhanced_queries(theme, use_cache=False)
    for i, q in enumerate(enhanced_queries, 1):
        print(f"  {i}. {q}")

    print(f"\n{'='*60}\n")


# Example usage for learning
if __name__ == "__main__":
    # Test query generation
    test_themes = [
        "hands",
        "dynamic poses",
        "portrait lighting",
        "vintage cars",
    ]

    for theme in test_themes:
        queries = generate_enhanced_queries(theme, use_cache=False)
        print(f"\n{theme.upper()}:")
        for q in queries:
            print(f"  - {q}")
