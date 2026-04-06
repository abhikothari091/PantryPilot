import logging
import re
from typing import Optional

from app.services.gluten_blocklist import GLUTEN_BLOCKLIST

logger = logging.getLogger(__name__)

STRICT_PROMPT_ADDENDUM = (
    "CRITICAL: The previous response contained a hidden-gluten ingredient. "
    "You MUST NOT use any of the following ingredients under any circumstances: "
    + ", ".join(sorted(GLUTEN_BLOCKLIST))
    + ". Double-check every ingredient before responding."
)

SAFE_FALLBACK_RESPONSE = {
    "error": "recipe_constraint_violation",
    "message": (
        "We were unable to generate a gluten-free recipe that meets your constraints. "
        "Please try again or adjust your ingredient selection."
    ),
    "recipe": None,
}


def find_blocklist_violations(recipe_text: str) -> list[str]:
    """Return any blocklisted ingredient names found in recipe_text."""
    recipe_lower = recipe_text.lower()
    violations = []
    for ingredient in GLUTEN_BLOCKLIST:
        # Match whole-word occurrences to avoid false positives
        pattern = r"\b" + re.escape(ingredient.lower()) + r"\b"
        if re.search(pattern, recipe_lower):
            violations.append(ingredient)
    return violations


async def generate_with_validation(generate_fn, prompt: str, call_llm) -> dict:
    """Call the LLM, validate output for gluten violations, retry once if needed.

    Args:
        generate_fn: Callable that accepts a prompt string and returns the raw
                     recipe text from the LLM.
        prompt: The original prompt to send on the first attempt.
        call_llm: Unused — kept for interface compatibility; pass generate_fn instead.

    Returns:
        A dict with a ``recipe`` key on success, or SAFE_FALLBACK_RESPONSE on
        repeated violation.
    """
    recipe_text = await generate_fn(prompt)

    violations = find_blocklist_violations(recipe_text)
    if not violations:
        return {"recipe": recipe_text}

    logger.warning(
        "Gluten violation detected on first attempt — violations=%s; retrying with strict prompt",
        violations,
    )

    strict_prompt = prompt + "\n\n" + STRICT_PROMPT_ADDENDUM
    retry_text = await generate_fn(strict_prompt)

    retry_violations = find_blocklist_violations(retry_text)
    if retry_violations:
        logger.error(
            "Gluten violation persists after retry — violations=%s; returning safe fallback",
            retry_violations,
        )
        return SAFE_FALLBACK_RESPONSE

    return {"recipe": retry_text}
