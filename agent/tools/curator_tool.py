"""
Curator Tool - Smart image curation for art practice.

Expands themes into multiple search queries and curates diverse image sets.
Uses cache-aware selection with scoring to provide fresh, relevant images.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.tools import tool
from services.pexels_client import pexels_client
from services.memory_store import memory_store
from services.session_store import session_store
from services.image_scorer import image_scorer
import config

# Days to look back for recently used images
EXCLUDE_RECENT_DAYS = getattr(config, 'EXCLUDE_RECENT_IMAGES_DAYS', 3)

# Theme to queries mapping for common art practice themes
THEME_EXPANSIONS = {
    # Animals
    "animals": ["cat", "dog", "horse", "bird"],
    "animal": ["cat", "dog", "horse", "bird"],
    "pets": ["cat", "dog", "rabbit", "hamster"],
    "wildlife": ["lion", "elephant", "deer", "wolf"],

    # Human body
    "hands": ["hand", "fist", "fingers", "grip"],
    "hand": ["hand", "fist", "fingers", "grip"],
    "hand studies": ["hand", "fist", "pointing", "grip"],
    "feet": ["foot", "barefoot", "toes", "walking"],
    "faces": ["portrait", "face", "profile", "smile"],
    "portrait": ["portrait", "face", "headshot", "profile"],
    "portraits": ["portrait", "face", "headshot", "profile"],

    # Poses
    "dynamic poses": ["dancer", "athlete", "runner", "gymnast"],
    "dynamic": ["dancer", "athlete", "jump", "action"],
    "poses": ["model", "pose", "standing", "sitting"],
    "gesture": ["dancer", "yoga", "stretch", "movement"],
    "gestures": ["dancer", "yoga", "stretch", "movement"],
    "figure": ["model", "pose", "figure", "body"],
    "figure drawing": ["model", "pose", "figure", "standing"],

    # Objects
    "vehicles": ["car", "motorcycle", "bicycle", "truck"],
    "cars": ["car", "sedan", "sports car", "vintage car"],
    "architecture": ["building", "house", "bridge", "tower"],
    "nature": ["tree", "flower", "mountain", "forest"],
    "food": ["fruit", "vegetables", "meal", "cooking"],
}


def _expand_theme(theme: str, use_llm_fallback: bool = True) -> list[str]:
    """Expand a theme into search queries.

    Args:
        theme: The practice theme
        use_llm_fallback: If True, use LLM to generate queries when no preset matches

    Returns:
        List of search queries
    """
    theme_lower = theme.lower().strip()

    # Check exact match in presets
    if theme_lower in THEME_EXPANSIONS:
        return THEME_EXPANSIONS[theme_lower]

    # Check partial match in presets
    for key, queries in THEME_EXPANSIONS.items():
        if key in theme_lower or theme_lower in key:
            return queries

    # No preset match - use LLM to generate smart queries
    if use_llm_fallback:
        try:
            from agent.subagents.query_generator import generate_smart_queries
            queries = generate_smart_queries(theme)
            if queries and len(queries) >= 2:
                return queries
        except Exception as e:
            print(f"[CURATOR] Smart query generation failed: {e}")

    # Final fallback: use theme as-is
    return [theme_lower]


def _is_good_reference(alt_text: str, theme: str = "") -> bool:
    """Check if image is good for reference practice using subagent."""
    from agent.subagents.image_evaluator import is_good_reference
    return is_good_reference(alt_text, theme)


def _get_cached_images_with_scores(theme: str) -> list[dict] | None:
    """Get cached images with their scores. Returns None if DB offline."""
    try:
        images = memory_store.get_cached_images_for_theme(theme)
        if images:
            print(f"[CURATOR] Cache has {len(images)} images for '{theme}'")
            return images
    except Exception as e:
        print(f"[CURATOR] Cache unavailable: {e}")
    return None


def _get_recently_used_ids() -> set[int]:
    """Get IDs of images used recently. Returns empty set if DB offline."""
    try:
        return session_store.get_images_shown_recently(days=EXCLUDE_RECENT_DAYS)
    except Exception:
        return set()


def _try_save_to_cache(theme: str, queries: list[str], images: list[dict]):
    """Try to save results to cache. Silently fails if DB offline."""
    try:
        memory_store.save_theme_results(theme, queries, images)
        print(f"[CURATOR] Saved to cache")
    except Exception:
        pass  # Silently ignore - DB offline


@tool
def curate_reference_photos(theme: str, target_count: int = 12, force_fresh: bool = False) -> list[dict]:
    """
    Curate diverse reference photos for art practice.

    Expands the theme into multiple search terms to get varied results.
    Uses smart caching and scoring to provide fresh, relevant images.
    Recently used images are deprioritized for variety.

    Args:
        theme: What to practice (e.g., "hands", "dynamic poses", "animals")
        target_count: Target number of images (default 12)
        force_fresh: If True, bypass cache AND preset query expansions.
                    Use this when user asks for "fresh", "new", "different" images.
                    The theme will be used directly as creative search terms.

    Returns:
        List of photo dicts with: pexels_id, url, thumbnail, alt, photographer
    """
    from agent.tools.session_control_tool import set_images_for_session

    print(f"[CURATOR] Curating: '{theme}' (force_fresh={force_fresh})")

    # Get recently used images to potentially exclude
    recently_used = _get_recently_used_ids()
    print(f"[CURATOR] Recently used: {len(recently_used)} images")

    available = []
    needed = target_count

    # Skip cache if force_fresh is requested
    if not force_fresh:
        # Check cache first
        cached_images = _get_cached_images_with_scores(theme)

        if cached_images:
            # Filter out recently used if we have enough remaining
            available = [img for img in cached_images if img['pexels_id'] not in recently_used]

            if len(available) >= target_count:
                # Use scorer for weighted selection from cache
                print(f"[CURATOR] Using cache ({len(available)} fresh images available)")
                try:
                    selected = image_scorer.select_images(
                        available=available,
                        theme=theme,
                        count=target_count,
                        exclude_ids=recently_used
                    )
                    if selected:
                        set_images_for_session(selected)
                        return selected
                except Exception as e:
                    print(f"[CURATOR] Scorer failed: {e}")
                    # Fallback to simple slice
                    result = available[:target_count]
                    set_images_for_session(result)
                    return result

            # Not enough fresh images in cache - supplement with API
            print(f"[CURATOR] Cache has {len(available)} fresh images, need {target_count}")
            needed = target_count - len(available)
    else:
        print(f"[CURATOR] Force fresh mode - bypassing cache and presets")

    # Determine search queries
    if force_fresh:
        # Force fresh: bypass presets, use LLM to generate intelligent queries
        print(f"[CURATOR] Force fresh mode - generating smart queries with LLM")
        try:
            from agent.subagents.query_generator import generate_smart_queries
            queries = generate_smart_queries(theme, use_cache=False)  # Don't cache for fresh requests
            print(f"[CURATOR] Fresh smart queries: {queries}")
        except Exception as e:
            print(f"[CURATOR] Smart query generation failed: {e}, using theme directly")
            queries = [theme]
    else:
        # Normal mode: expand theme to queries using presets (with LLM fallback)
        queries = _expand_theme(theme)
        print(f"[CURATOR] Queries: {queries}")

    # Search and collect new images from API
    new_images = []
    # Fetch more than needed for variety and scoring
    fetch_per_query = max(10, (needed * 2) // len(queries) + 3)

    for query in queries:
        print(f"[CURATOR] Searching: '{query}'")
        try:
            photos = pexels_client.search_photos(query=query, per_page=fetch_per_query)

            for photo in photos:
                if _is_good_reference(photo.alt, theme):
                    # Skip duplicates and recently used
                    pexels_id = photo.id
                    if pexels_id in recently_used:
                        continue
                    if any(img.get("pexels_id") == pexels_id for img in available):
                        continue
                    if any(img.get("pexels_id") == pexels_id for img in new_images):
                        continue

                    new_images.append({
                        "pexels_id": pexels_id,
                        "url": photo.src_large,
                        "thumbnail": photo.src_medium,
                        "alt": photo.alt,
                        "photographer": photo.photographer,
                        "times_used": 0,  # New images
                    })

        except Exception as e:
            print(f"[CURATOR] Search failed for '{query}': {e}")
            continue

    # Combine available cached images with new ones
    all_images = available + new_images
    print(f"[CURATOR] Total available: {len(all_images)} images")

    # Use scorer for final selection
    try:
        final_images = image_scorer.select_images(
            available=all_images,
            theme=theme,
            count=target_count,
            exclude_ids=recently_used
        )
    except Exception as e:
        print(f"[CURATOR] Scorer failed: {e}")
        final_images = all_images[:target_count]

    print(f"[CURATOR] Selected: {len(final_images)} images")

    # Cache new images for future use (skip if force_fresh - user wanted fresh, don't pollute preferences)
    if new_images and not force_fresh:
        _try_save_to_cache(theme, queries, new_images)

    # Set images for session control
    set_images_for_session(final_images)

    return final_images
