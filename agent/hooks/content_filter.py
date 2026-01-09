"""
Hooks for the art practice agent tools.

This module demonstrates Agno's hook system with:
- Pre-hooks: Run before tool execution (logging, query enhancement)
- Post-hooks: Run after tool execution (filtering, validation)
"""

from agno.tools import FunctionCall
from datetime import datetime


def log_pre_hook(fc: FunctionCall) -> None:
    """Pre-hook: Log tool calls for debugging and monitoring.

    This hook runs before the tool executes and logs:
    - Tool name
    - Arguments passed
    - Timestamp
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Tool called: {fc.function.name}")
    print(f"  Arguments: {fc.arguments}")


def log_post_hook(fc: FunctionCall) -> None:
    """Post-hook: Log tool results for debugging.

    This hook runs after the tool executes and logs:
    - Tool name
    - Result summary
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    result = fc.result

    if isinstance(result, list):
        print(f"[{timestamp}] {fc.function.name} returned {len(result)} items")
    elif isinstance(result, dict):
        print(f"[{timestamp}] {fc.function.name} returned dict with keys: {list(result.keys())}")
    else:
        print(f"[{timestamp}] {fc.function.name} completed")


def enhance_query_hook(fc: FunctionCall) -> None:
    """Pre-hook: Enhance search queries for better artistic results.

    This hook modifies the query arguments to improve search results
    by adding art-related terms when appropriate.

    Note: This demonstrates how pre-hooks can modify function arguments
    before execution.
    """
    if fc.function.name == "search_reference_photos" and fc.arguments:
        query = fc.arguments.get("query", "")

        art_terms = ["reference", "drawing", "art", "artistic", "pose"]
        has_art_term = any(term in query.lower() for term in art_terms)

        if not has_art_term and query:
            fc.arguments["query"] = f"{query} reference"
            print(f"  Query enhanced: '{query}' -> '{fc.arguments['query']}'")


# Future implementation placeholder
def nsfw_filter_post_hook(fc: FunctionCall) -> None:
    """Post-hook: Filter potentially inappropriate images.

    This is a placeholder for future NSFW filtering functionality.
    Would integrate with image classification or use Pexels safe search.

    Implementation ideas:
    - Check image metadata for flags
    - Use ML model to classify images
    - Filter based on certain search terms
    - Respect user age settings
    """
    pass
