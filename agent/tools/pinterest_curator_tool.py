"""
Pinterest Curator Tool - MCP-powered image curation for your agent.

This tool replaces/augments Pexels with Pinterest via MCP, downloads images,
and integrates seamlessly with your existing PySide6 GUI.

Uses smart query expansion to generate diverse search queries from user themes,
similar to the Pexels curator approach.
"""

import sys
from pathlib import Path
import time
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.tools import tool
from agent.hooks import log_pre_hook
from services.image_downloader import download_images_sync
from services.mcp_client import PinterestMCPClient
from agent.tools.session_control_tool import set_images_for_session
import asyncio
import logging

# Setup Pinterest-specific logger
pinterest_logger = logging.getLogger('Pinterest')
pinterest_logger.setLevel(logging.INFO)


# Pinterest-optimized theme expansions for art reference searches
# These are more specific and concrete than generic search terms
PINTEREST_THEME_EXPANSIONS = {
    # Human body - hands
    "hands": ["pianist hands closeup", "rock climbing grip", "potter hands clay", "sign language gesture"],
    "hand": ["pianist hands closeup", "rock climbing grip", "potter hands clay", "sign language gesture"],
    "hand studies": ["hand anatomy drawing", "foreshortened hand pose", "hand grip reference", "expressive hands"],

    # Human body - feet
    "feet": ["ballet feet pointe", "barefoot beach walking", "running feet motion", "toe closeup"],
    "foot": ["ballet feet pointe", "barefoot beach walking", "running feet motion", "toe closeup"],

    # Faces and portraits
    "faces": ["portrait photography lighting", "face profile silhouette", "emotional expression portrait", "character face closeup"],
    "face": ["portrait photography lighting", "face profile silhouette", "emotional expression portrait", "character face closeup"],
    "portrait": ["portrait photography lighting", "headshot professional", "dramatic portrait shadow", "natural light portrait"],
    "portraits": ["portrait photography lighting", "headshot professional", "dramatic portrait shadow", "natural light portrait"],

    # Poses and figures
    "dynamic poses": ["ballet dancer leap", "parkour jump action", "martial arts kick", "gymnast pose"],
    "dynamic": ["ballet dancer leap", "parkour jump action", "martial arts kick", "gymnast pose"],
    "poses": ["figure model pose", "fashion model standing", "yoga pose silhouette", "dance pose elegant"],
    "gesture": ["dancer movement gesture", "yoga stretch pose", "expressive body movement", "contemporary dance"],
    "figure": ["figure drawing model", "nude art reference", "body pose study", "anatomy reference"],
    "figure drawing": ["figure model pose", "gesture drawing reference", "life drawing pose", "anatomy study pose"],

    # Animals
    "animals": ["cat portrait closeup", "dog action running", "horse galloping", "bird flight wings"],
    "animal": ["cat portrait closeup", "dog action running", "horse galloping", "bird flight wings"],
    "pets": ["cat sleeping cute", "dog portrait loyal", "rabbit fluffy", "pet photography"],
    "wildlife": ["lion portrait majestic", "elephant nature", "deer forest", "wolf wild"],

    # Vehicles
    "vehicles": ["classic car vintage", "motorcycle rider", "bicycle street", "truck industrial"],
    "cars": ["classic Cadillac car", "1960s Mustang vintage", "sports car dramatic", "vintage automobile"],
    "vintage cars": ["classic Cadillac car", "1960s Mustang vintage", "antique car show", "retro automobile"],

    # Architecture and objects
    "architecture": ["building dramatic angle", "modern architecture lines", "historic building facade", "bridge structure"],
    "nature": ["tree dramatic lighting", "flower macro closeup", "mountain landscape", "forest atmosphere"],
    "food": ["fruit still life", "cooking action hands", "meal plating artistic", "food photography"],

    # Style-specific
    "vintage": ["1950s fashion model", "retro pin-up style", "classic hollywood glamour", "vintage fashion photography"],
    "vintage style": ["1950s fashion photography", "retro pin-up model", "classic hollywood portrait", "vintage dress photoshoot"],
    "vintage style model": ["1950s fashion photography", "retro pin-up model", "classic hollywood portrait", "vintage dress photoshoot"],
}


def _expand_pinterest_theme(theme: str) -> list[str]:
    """
    Expand a theme into Pinterest-optimized search queries.

    Uses preset expansions for common themes, falls back to LLM-based
    smart query generation for unknown themes.

    Args:
        theme: The user's practice theme

    Returns:
        List of 4-6 specific search queries optimized for Pinterest
    """
    theme_lower = theme.lower().strip()

    # Check exact match in presets
    if theme_lower in PINTEREST_THEME_EXPANSIONS:
        queries = PINTEREST_THEME_EXPANSIONS[theme_lower]
        pinterest_logger.info(f"Using preset queries for '{theme}': {queries}")
        return queries

    # Check partial match in presets
    for key, queries in PINTEREST_THEME_EXPANSIONS.items():
        if key in theme_lower or theme_lower in key:
            pinterest_logger.info(f"Using partial match '{key}' for '{theme}': {queries}")
            return queries

    # No preset match - use LLM to generate smart queries
    pinterest_logger.info(f"No preset found for '{theme}', using smart query generation")
    try:
        from agent.subagents.query_generator import generate_smart_queries
        queries = generate_smart_queries(theme)
        if queries and len(queries) >= 2:
            pinterest_logger.info(f"Smart queries generated: {queries}")
            return queries
    except Exception as e:
        pinterest_logger.warning(f"Smart query generation failed: {e}")

    # Final fallback: use theme as-is with "reference" suffix for better art results
    fallback = [f"{theme} reference", f"{theme} art", theme]
    pinterest_logger.info(f"Using fallback queries: {fallback}")
    return fallback


@tool(pre_hook=log_pre_hook)
def curate_pinterest_images(theme: str, count: int = 15) -> list[dict]:
    """
    Curate images from Pinterest using MCP, download them, and prepare for display.

    This tool:
    1. Expands theme into diverse, specific search queries
    2. Searches Pinterest via MCP server with multiple queries
    3. Downloads images to local cache
    4. Returns paths ready for PySide6 QPixmap loading

    Args:
        theme: Practice theme (e.g., "figure drawing", "hand anatomy")
        count: Number of images to curate (default 15)

    Returns:
        List of image dictionaries with local file paths and metadata
    """
    start_time = time.time()
    timestamp = datetime.now().strftime("%H:%M:%S")

    pinterest_logger.info("=" * 70)
    pinterest_logger.info(f"🎨 PINTEREST CURATION STARTED - {timestamp}")
    pinterest_logger.info(f"📝 Theme: '{theme}'")
    pinterest_logger.info(f"🔢 Requested: {count} images")
    pinterest_logger.info("=" * 70)

    # Expand theme into diverse queries
    queries = _expand_pinterest_theme(theme)
    images_per_query = max(3, (count + len(queries) - 1) // len(queries))  # Ceiling division

    pinterest_logger.info(f"🔍 Expanded to {len(queries)} queries: {queries}")
    pinterest_logger.info(f"🔢 Images per query: {images_per_query}")

    # Get server path
    server_path = str(Path(__file__).parent.parent.parent / "mcp_servers" / "pinterest_server.py")

    # Search Pinterest via MCP using diverse search for better variety
    async def search():
        async with PinterestMCPClient(server_path) as client:
            return await client.search_diverse(queries, images_per_query)

    # Run async search
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    pinterest_logger.info("🔌 Connecting to Pinterest MCP server...")
    mcp_start = time.time()

    try:
        results = loop.run_until_complete(search())
        mcp_time = time.time() - mcp_start
        pinterest_logger.info(f"✓ MCP diverse search completed in {mcp_time:.2f}s")
    except Exception as e:
        pinterest_logger.error(f"✗ MCP search failed: {e}")
        import traceback
        traceback.print_exc()
        return []

    if not results:
        pinterest_logger.warning("⚠ No results found from Pinterest")
        return []

    pinterest_logger.info(f"📸 Found {len(results)} diverse Pinterest pins")

    # Check if using real Pinterest or mock data
    is_mock = any('mock' in r.get('id', '') for r in results[:1])
    if is_mock:
        pinterest_logger.warning("⚠ Using MOCK data (Pinterest credentials not configured)")
        pinterest_logger.info("   → Add PINTEREST_EMAIL and PINTEREST_PASSWORD to .env for real data")
    else:
        pinterest_logger.info("✓ Using REAL Pinterest data")

    # Download images
    pinterest_logger.info("⬇ Downloading images to cache...")
    download_start = time.time()

    image_urls = [img['image_url'] for img in results]
    local_paths = download_images_sync(image_urls)

    download_time = time.time() - download_start
    pinterest_logger.info(f"✓ Download completed in {download_time:.2f}s")

    # Build response with local paths
    curated_images = []
    failed_count = 0

    for i, (result, local_path) in enumerate(zip(results, local_paths)):
        if local_path is None:
            pinterest_logger.warning(f"✗ Failed to download image {i+1}/{len(results)}")
            failed_count += 1
            continue

        # Determine if this is a real Pinterest image or Pexels fallback
        result_id = result.get('id', '')
        is_pinterest = result_id.startswith('pinterest_')
        is_pexels = result_id.startswith('pexels_')

        curated_images.append({
            "pexels_id": result_id,  # Keep same format as Pexels tool for compatibility
            "id": result_id,
            "pin_id": result.get('pin_id'),  # Actual Pinterest pin ID for repinning (None for Pexels)
            "url": str(local_path),  # LOCAL PATH for fast loading
            "thumbnail": result['thumbnail_url'],
            "alt": result['title'],
            "photographer": result['creator'],
            "description": result.get('description', ''),
            "source": "Pinterest" if is_pinterest else "Pexels",
            "is_pinterest": is_pinterest,  # Flag for UI to check
            "pinterest_url": result['source_url'],  # Original Pinterest link
        })

    total_time = time.time() - start_time

    # Final summary
    pinterest_logger.info("=" * 70)
    pinterest_logger.info("📊 CURATION SUMMARY")
    pinterest_logger.info(f"✓ Successfully curated: {len(curated_images)}/{count} images")
    if failed_count > 0:
        pinterest_logger.warning(f"✗ Failed downloads: {failed_count}")
    pinterest_logger.info(f"⏱ Total time: {total_time:.2f}s")
    pinterest_logger.info(f"💾 Images cached for instant reuse")
    pinterest_logger.info("=" * 70)

    # Set images for session control - enables prepare_session_preview and start_practice_session
    set_images_for_session(curated_images)
    pinterest_logger.info("📋 Images registered with session control")

    return curated_images


@tool(pre_hook=log_pre_hook)
def curate_pinterest_diverse(queries: list[str], per_query: int = 4) -> list[dict]:
    """
    Curate diverse images from Pinterest using multiple queries.

    This provides better variety by searching different aspects of a theme.

    Args:
        queries: List of specific search queries
                Example: ["hand anatomy", "foreshortened hand", "hand gesture"]
        per_query: Images per query (default 4)

    Returns:
        List of curated images with local paths
    """
    start_time = time.time()
    timestamp = datetime.now().strftime("%H:%M:%S")

    pinterest_logger.info("=" * 70)
    pinterest_logger.info(f"🎨 DIVERSE PINTEREST CURATION - {timestamp}")
    pinterest_logger.info(f"📝 Queries: {queries}")
    pinterest_logger.info(f"🔢 Per query: {per_query} images (Total: ~{len(queries) * per_query})")
    pinterest_logger.info("=" * 70)

    server_path = str(Path(__file__).parent.parent.parent / "mcp_servers" / "pinterest_server.py")

    async def search():
        async with PinterestMCPClient(server_path) as client:
            return await client.search_diverse(queries, per_query)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    pinterest_logger.info("🔌 Connecting to Pinterest MCP server...")
    mcp_start = time.time()

    try:
        results = loop.run_until_complete(search())
        mcp_time = time.time() - mcp_start
        pinterest_logger.info(f"✓ Diverse MCP search completed in {mcp_time:.2f}s")
    except Exception as e:
        pinterest_logger.error(f"✗ Diverse search failed: {e}")
        import traceback
        traceback.print_exc()
        return []

    if not results:
        pinterest_logger.warning("⚠ No diverse results found")
        return []

    pinterest_logger.info(f"📸 Found {len(results)} diverse Pinterest pins")

    # Check for mock data
    is_mock = any('mock' in r.get('id', '') for r in results[:1])
    if is_mock:
        pinterest_logger.warning("⚠ Using MOCK data")
    else:
        pinterest_logger.info("✓ Using REAL Pinterest data")

    # Download
    pinterest_logger.info("⬇ Downloading diverse images...")
    download_start = time.time()

    image_urls = [img['image_url'] for img in results]
    local_paths = download_images_sync(image_urls)

    download_time = time.time() - download_start
    pinterest_logger.info(f"✓ Download completed in {download_time:.2f}s")

    # Build response
    curated_images = []
    failed_count = 0

    for result, local_path in zip(results, local_paths):
        if local_path:
            # Determine if this is a real Pinterest image or Pexels fallback
            result_id = result.get('id', '')
            is_pinterest = result_id.startswith('pinterest_')

            curated_images.append({
                "pexels_id": result_id,
                "id": result_id,
                "pin_id": result.get('pin_id'),  # Actual Pinterest pin ID for repinning
                "url": str(local_path),
                "thumbnail": result['thumbnail_url'],
                "alt": result['title'],
                "photographer": result['creator'],
                "description": result.get('description', ''),
                "source": "Pinterest" if is_pinterest else "Pexels",
                "is_pinterest": is_pinterest,
                "pinterest_url": result['source_url'],
            })
        else:
            failed_count += 1

    total_time = time.time() - start_time

    pinterest_logger.info("=" * 70)
    pinterest_logger.info("📊 DIVERSE CURATION SUMMARY")
    pinterest_logger.info(f"✓ Successfully curated: {len(curated_images)} images")
    if failed_count > 0:
        pinterest_logger.warning(f"✗ Failed downloads: {failed_count}")
    pinterest_logger.info(f"⏱ Total time: {total_time:.2f}s")
    pinterest_logger.info("=" * 70)

    # Set images for session control - enables prepare_session_preview and start_practice_session
    set_images_for_session(curated_images)
    pinterest_logger.info("📋 Images registered with session control")

    return curated_images
