import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.tools import tool, FunctionCall
from services.pexels_client import pexels_client
from agent.hooks import log_pre_hook, enhance_query_hook


@tool(pre_hook=log_pre_hook)
def search_reference_photos(query: str, count: int = 10) -> list[dict]:
    """Search for artist reference photos on Pexels.

    Use this tool to find reference images for art practice sessions.
    The query should be optimized for finding good artistic references.

    Args:
        query: Search terms for finding reference photos.
              Examples: "figure drawing pose", "hand reference", "portrait lighting",
              "vehicle side view", "animal anatomy", "gesture dynamic pose"
        count: Number of photos to retrieve (default 10, max 80)

    Returns:
        List of photo dictionaries with url, photographer, and alt text
    """
    photos = pexels_client.search_photos(query=query, per_page=count)
    print(f"[PEXELS] Found {len(photos)} photos for '{query}'")

    return [
        {
            "id": photo.id,
            "url": photo.src_large,
            "thumbnail": photo.src_medium,
            "photographer": photo.photographer,
            "alt": photo.alt,
        }
        for photo in photos
    ]
