"""
Image Curator Subagent.

Specializes in intelligent image curation for art reference practice.
- Expands themes into multiple search queries
- Performs greedy image evaluation
- Caches results in PostgreSQL for reuse
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.agent import Agent
from agno.tools import tool
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.models.openai.like import OpenAILike

from services.pexels_client import pexels_client
from services.memory_store import memory_store
import config


CURATOR_INSTRUCTIONS = """You curate images for QUICK SKETCH practice (30 sec to 2 min drawings).

## WORKFLOW (2 steps only)

1. Call check_theme_cache(theme). If found=true, return the images immediately.

2. If no cache, call curate_and_save(theme, queries) with 4 SIMPLE query terms.
   This tool searches, filters, saves to DB, and returns images - all in one call.

## CRITICAL: SIMPLE SEARCH TERMS (1-2 words each!)

GOOD: ["cat", "dog", "bird", "horse"] for "animals"
GOOD: ["dancer", "athlete", "runner", "gymnast"] for "dynamic poses"
GOOD: ["hand", "fist", "pointing", "grip"] for "hands"

BAD: ["cat anatomy detailed"] ❌ TOO LONG
BAD: ["dynamic dancer movement"] ❌ TOO LONG

## OUTPUT
Return the images list. No explanation needed.
"""


@tool
def check_theme_cache(theme: str) -> dict:
    """
    Check if we have cached results for this theme.

    Args:
        theme: The theme/term to check

    Returns:
        Dict with 'found' boolean. If found=True, also includes 'queries' and 'images'.
    """
    print(f"[CURATOR] Checking cache for theme: {theme}")

    try:
        cached = memory_store.get_cached_theme(theme)
        if cached:
            print(f"[CURATOR] Cache HIT! Found {len(cached['images'])} images")
            return {
                "found": True,
                "queries": cached["queries"],
                "images": cached["images"]
            }
        else:
            print(f"[CURATOR] Cache MISS for theme: {theme}")
            return {"found": False}
    except Exception as e:
        print(f"[CURATOR] Cache check failed (DB may be offline): {e}")
        return {"found": False, "error": str(e)}


@tool
def curate_and_save(theme: str, queries: list[str]) -> list[dict]:
    """
    Search, filter, and save curated images in ONE call.

    Args:
        theme: The theme to curate for
        queries: List of 4 SIMPLE search terms (1-2 words each!)
                Example: ["cat", "dog", "bird", "horse"]

    Returns:
        List of curated images (10-15 images)
    """
    print(f"[CURATOR] Curating '{theme}' with queries: {queries}")

    all_images = []

    for query in queries[:4]:
        print(f"[CURATOR] Searching: '{query}'")
        try:
            photos = pexels_client.search_photos(query=query, per_page=5)

            for photo in photos:
                if _is_good_reference(photo.alt, theme):
                    all_images.append({
                        "pexels_id": photo.id,
                        "url": photo.src_large,
                        "thumbnail": photo.src_medium,
                        "alt": photo.alt,
                        "photographer": photo.photographer,
                    })
                if len(all_images) >= 15:
                    break

            print(f"[CURATOR] Total: {len(all_images)} images")

        except Exception as e:
            print(f"[CURATOR] Search failed for '{query}': {e}")
            continue

        if len(all_images) >= 15:
            break

    # Ensure minimum images
    if len(all_images) < 10:
        print(f"[CURATOR] Only {len(all_images)}, fetching more...")
        for query in queries[:4]:
            try:
                photos = pexels_client.search_photos(query=query, per_page=5)
                for photo in photos:
                    if not any(img["pexels_id"] == photo.id for img in all_images):
                        all_images.append({
                            "pexels_id": photo.id,
                            "url": photo.src_large,
                            "thumbnail": photo.src_medium,
                            "alt": photo.alt,
                            "photographer": photo.photographer,
                        })
                    if len(all_images) >= 12:
                        break
            except:
                continue
            if len(all_images) >= 12:
                break

    final_images = all_images[:15]
    print(f"[CURATOR] Final: {len(final_images)} images")

    # Auto-save to memory (ignore errors - DB might be offline)
    try:
        memory_store.save_theme_results(theme, queries[:4], final_images)
        print(f"[CURATOR] Saved to memory")
    except Exception as e:
        print(f"[CURATOR] Could not save to memory (DB offline?): {e}")

    return final_images


def _is_good_reference(alt_text: str, theme: str) -> bool:
    """Simple keyword-based filter. No LLM needed."""
    if not alt_text:
        return True

    alt_lower = alt_text.lower()

    # Reject obvious bad matches
    bad_keywords = ["logo", "icon", "text", "screenshot", "graph", "chart", "diagram"]
    if any(bad in alt_lower for bad in bad_keywords):
        return False

    return True


def get_curator_model():
    """Get the configured LLM model for the curator agent."""
    provider = config.LLM_PROVIDER.lower()

    if provider == "moonshot":
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


def create_image_curator_agent() -> Agent:
    """Create and return the image curator subagent."""
    print("[CURATOR] Creating ImageCuratorAgent")

    agent = Agent(
        name="ImageCurator",
        model=get_curator_model(),
        instructions=CURATOR_INSTRUCTIONS,
        tools=[check_theme_cache, curate_and_save],
        markdown=True,
    )

    return agent


# Type alias for clarity
ImageCuratorAgent = Agent
