import hashlib
import json
import logging
import sys
from typing import Optional

# Structured JSON logger for gluten-free recipe generation monitoring
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))

gluten_logger = logging.getLogger("pantrypilot.gluten_monitor")
gluten_logger.setLevel(logging.INFO)
gluten_logger.addHandler(_handler)
gluten_logger.propagate = False


def _anonymize_user_id(user_id: str) -> str:
    """SHA-256 prefix so logs are queryable but not personally identifiable."""
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:16]


def log_gluten_free_generation(
    user_id: str,
    is_gluten_free: bool,
    blocklist_hit: bool,
    flagged_ingredient: Optional[str],
    retry_triggered: bool,
    final_status: str,
) -> None:
    """Emit a structured log entry for every gluten-free recipe generation request.

    Args:
        user_id: Raw user identifier — will be anonymized before logging.
        is_gluten_free: Whether the user's dietary profile has gluten-free set.
        blocklist_hit: True if the LLM output contained a blocklisted ingredient.
        flagged_ingredient: The first ingredient that triggered a blocklist match, or None.
        retry_triggered: True if the stricter-prompt retry was attempted.
        final_status: Outcome string, e.g. "ok", "violation_after_retry", "retry_clean".
    """
    entry = {
        "event": "gluten_free_recipe_generation",
        "user_hash": _anonymize_user_id(user_id),
        "dietary_flag_gluten_free": is_gluten_free,
        "blocklist_hit": blocklist_hit,
        "flagged_ingredient": flagged_ingredient,
        "retry_triggered": retry_triggered,
        "final_status": final_status,
    }
    gluten_logger.info(json.dumps(entry))
