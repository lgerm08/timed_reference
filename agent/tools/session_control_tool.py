"""
Session Control Tools - Agent-controlled session management.

These tools allow the agent to configure and control practice sessions,
including duration, image count, previews, and session start.
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.tools import tool

# Session configuration singleton - shared between agent and GUI
_session_config = {
    "duration_seconds": 60,
    "image_count": 10,
    "images": [],
    "preview_ready": False,
    "session_started": False,
    "theme": "",
}

# Valid duration options (seconds)
VALID_DURATIONS = [30, 60, 120, 300, 600]

# Max images per session
MAX_IMAGES = 15


def get_current_config() -> dict:
    """Get the current session configuration (for GUI to access)."""
    return _session_config.copy()


def set_images_for_session(images: list[dict]):
    """Set images for the session (called after curation)."""
    _session_config["images"] = images[:MAX_IMAGES]
    _session_config["preview_ready"] = False
    _session_config["session_started"] = False


def reset_session_state():
    """Reset session state (called when starting new session)."""
    _session_config["images"] = []
    _session_config["preview_ready"] = False
    _session_config["session_started"] = False


@tool
def set_session_duration(seconds: int) -> str:
    """
    Set the duration per image for the practice session.

    Args:
        seconds: Duration in seconds. Valid options: 30 (gesture), 60 (quick study),
                120 (study), 300 (detailed), 600 (full study)

    Returns:
        Confirmation message
    """
    if seconds not in VALID_DURATIONS:
        # Find closest valid duration
        closest = min(VALID_DURATIONS, key=lambda x: abs(x - seconds))
        _session_config["duration_seconds"] = closest
        return f"Duration set to {closest} seconds (closest valid option to {seconds}s). Valid options: {VALID_DURATIONS}"

    _session_config["duration_seconds"] = seconds

    # Friendly names
    duration_names = {
        30: "30 seconds (quick gesture)",
        60: "1 minute (gesture + shapes)",
        120: "2 minutes (study)",
        300: "5 minutes (detailed study)",
        600: "10 minutes (full study)",
    }

    return f"Duration set to {duration_names.get(seconds, f'{seconds} seconds')}"


@tool
def set_image_count(count: int) -> str:
    """
    Set the number of images for the practice session.

    Args:
        count: Number of images (1-15)

    Returns:
        Confirmation message
    """
    if count < 1:
        count = 1
    elif count > MAX_IMAGES:
        count = MAX_IMAGES

    _session_config["image_count"] = count

    # Trim images if we have more than needed
    if len(_session_config["images"]) > count:
        _session_config["images"] = _session_config["images"][:count]

    total_time = count * _session_config["duration_seconds"]
    minutes = total_time // 60

    return f"Image count set to {count}. Total session time: ~{minutes} minutes"


@tool
def get_session_config() -> dict:
    """
    Get the current session configuration.

    Returns:
        Dict with duration_seconds, image_count, images_loaded, preview_ready
    """
    return {
        "duration_seconds": _session_config["duration_seconds"],
        "image_count": _session_config["image_count"],
        "images_loaded": len(_session_config["images"]),
        "preview_ready": _session_config["preview_ready"],
        "theme": _session_config["theme"],
        "total_time_minutes": (_session_config["duration_seconds"] * _session_config["image_count"]) // 60,
    }


@tool
def prepare_session_preview(images: Optional[list[dict]] = None) -> dict:
    """
    Prepare preview thumbnails for user approval.

    Call this after curating images to show the user what they'll be practicing with.
    The GUI will display thumbnails when this is called.

    Args:
        images: Optional list of image dicts. If not provided, uses previously set images.

    Returns:
        Dict with preview status and image count
    """
    if images:
        # Normalize image keys
        normalized = []
        for img in images[:MAX_IMAGES]:
            normalized_img = dict(img)
            if "pexels_id" in normalized_img and "id" not in normalized_img:
                normalized_img["id"] = normalized_img["pexels_id"]
            normalized.append(normalized_img)
        _session_config["images"] = normalized

    if not _session_config["images"]:
        return {
            "success": False,
            "message": "No images available for preview. Please search for images first.",
            "image_count": 0,
        }

    _session_config["preview_ready"] = True

    # Return preview info - GUI will handle displaying thumbnails
    preview_images = []
    for img in _session_config["images"][:_session_config["image_count"]]:
        preview_images.append({
            "id": img.get("id") or img.get("pexels_id"),
            "thumbnail": img.get("thumbnail"),
            "alt": img.get("alt", "Reference photo"),
            "photographer": img.get("photographer", "Unknown"),
        })

    return {
        "success": True,
        "message": f"Preview ready with {len(preview_images)} images. Ask the user if they'd like to start or see different images.",
        "image_count": len(preview_images),
        "images": preview_images,
        "duration_per_image": _session_config["duration_seconds"],
        "total_time_minutes": (_session_config["duration_seconds"] * len(preview_images)) // 60,
    }


@tool
def start_practice_session(theme: str = "") -> dict:
    """
    Start the practice session with current configuration.

    Only call this when:
    1. Images have been curated and previewed
    2. User has approved the image set
    3. User explicitly wants to start

    Args:
        theme: Optional theme name for the session

    Returns:
        Dict with session start status
    """
    if not _session_config["images"]:
        return {
            "success": False,
            "message": "No images loaded. Please search for images first.",
            "action": "search_images",
        }

    if not _session_config["preview_ready"]:
        return {
            "success": False,
            "message": "Please show the user a preview first before starting.",
            "action": "prepare_preview",
        }

    # Mark session as ready to start - GUI will pick this up
    _session_config["session_started"] = True
    _session_config["theme"] = theme

    count = min(_session_config["image_count"], len(_session_config["images"]))
    duration = _session_config["duration_seconds"]
    total_minutes = (count * duration) // 60

    return {
        "success": True,
        "message": f"Starting {theme or 'practice'} session! {count} images, {duration} seconds each ({total_minutes} minutes total). Good luck!",
        "image_count": count,
        "duration_seconds": duration,
        "total_time_minutes": total_minutes,
        "theme": theme,
        "action": "session_starting",
    }
