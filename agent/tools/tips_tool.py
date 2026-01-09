from agno.tools import tool


@tool
def get_practice_tips(practice_focus: str, duration_minutes: int = 5) -> dict:
    """Get practice tips and recommendations for the artist.

    Use this tool to provide helpful guidance based on what the artist
    wants to practice and their session duration.

    Args:
        practice_focus: What the artist wants to practice.
                        Examples: "hands", "gestures", "figure drawing", "portraits",
                        "vehicles", "animals", "shading", "perspective"
        duration_minutes: How long each sketch will be in minutes (1, 2, 5, 10, etc.)

    Returns:
        Dictionary with tips, focus areas, and warm-up suggestions
    """
    tips_database = {
        "hands": {
            "focus_areas": [
                "Observe the overall gesture before details",
                "Pay attention to finger proportions",
                "Notice how fingers overlap and foreshorten",
                "Study the palm's planes and creases",
            ],
            "common_mistakes": [
                "Making fingers the same length",
                "Forgetting the thumb's unique angle",
                "Ignoring the hand's overall shape",
            ],
            "warm_up": "Draw 5 quick hand silhouettes in 30 seconds each",
        },
        "gestures": {
            "focus_areas": [
                "Capture the line of action first",
                "Look for the rhythm and flow",
                "Exaggerate the pose slightly",
                "Focus on weight distribution",
            ],
            "common_mistakes": [
                "Starting with details instead of gesture",
                "Making poses too stiff",
                "Ignoring the center of gravity",
            ],
            "warm_up": "Do 10 one-minute gesture drawings to loosen up",
        },
        "figure drawing": {
            "focus_areas": [
                "Establish proportions with head measurements",
                "Find the gesture line first",
                "Block in major masses before details",
                "Observe negative space",
            ],
            "common_mistakes": [
                "Starting with the head too large",
                "Forgetting to check proportions",
                "Adding details too early",
            ],
            "warm_up": "Draw stick figures capturing poses in 15 seconds each",
        },
        "portraits": {
            "focus_areas": [
                "Map facial landmarks accurately",
                "Observe light and shadow shapes",
                "Pay attention to the head's 3D form",
                "Study eye placement (halfway down the head)",
            ],
            "common_mistakes": [
                "Making eyes too high on the face",
                "Forgetting the skull's volume",
                "Overdetailing one area",
            ],
            "warm_up": "Draw egg shapes with cross contours for head angles",
        },
        "vehicles": {
            "focus_areas": [
                "Start with basic 3D shapes (boxes, cylinders)",
                "Establish perspective lines first",
                "Observe wheel ellipses carefully",
                "Notice reflections and surface changes",
            ],
            "common_mistakes": [
                "Inconsistent perspective",
                "Wheels not aligned properly",
                "Ignoring the vehicle's weight",
            ],
            "warm_up": "Practice drawing boxes in perspective",
        },
        "shading": {
            "focus_areas": [
                "Identify the light source first",
                "Squint to see value groups",
                "Build values gradually",
                "Pay attention to reflected light",
            ],
            "common_mistakes": [
                "Making shadows too light",
                "Forgetting ambient occlusion",
                "Overblending everything",
            ],
            "warm_up": "Shade a sphere to practice core shadow and highlights",
        },
    }

    practice_focus_lower = practice_focus.lower()
    tips = None

    for key in tips_database:
        if key in practice_focus_lower or practice_focus_lower in key:
            tips = tips_database[key]
            break

    if tips is None:
        tips = {
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
            "warm_up": f"Do quick thumbnail sketches of {practice_focus} to warm up",
        }

    duration_advice = ""
    if duration_minutes <= 1:
        duration_advice = "Focus only on gesture and major shapes. No details!"
    elif duration_minutes <= 2:
        duration_advice = "Capture gesture first, then block in major forms."
    elif duration_minutes <= 5:
        duration_advice = "You have time for gesture, forms, and basic proportions."
    elif duration_minutes <= 10:
        duration_advice = "Include gesture, forms, proportions, and start adding key details."
    else:
        duration_advice = "Full study: gesture, forms, proportions, details, and some shading."

    return {
        "practice_focus": practice_focus,
        "duration_minutes": duration_minutes,
        "duration_advice": duration_advice,
        "focus_areas": tips["focus_areas"],
        "common_mistakes": tips["common_mistakes"],
        "warm_up_suggestion": tips["warm_up"],
    }
