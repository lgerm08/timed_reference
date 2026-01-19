"""Subagents package for specialized agent tasks."""

from agent.subagents.image_curator import create_image_curator_agent, ImageCuratorAgent
from agent.subagents.tips_generator import generate_practice_tips, TipsGenerator
from agent.subagents.image_evaluator import (
    evaluate_image,
    is_good_reference,
    ImageEvaluator,
)
from agent.subagents.query_generator import (
    generate_smart_queries,
    QueryGenerator,
)

__all__ = [
    "create_image_curator_agent",
    "ImageCuratorAgent",
    "generate_practice_tips",
    "TipsGenerator",
    "evaluate_image",
    "is_good_reference",
    "ImageEvaluator",
    "generate_smart_queries",
    "QueryGenerator",
]
