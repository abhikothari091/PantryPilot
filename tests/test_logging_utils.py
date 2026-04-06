import json
import logging

import pytest

from backend.app.logging_utils import (
    _anonymize_user_id,
    gluten_logger,
    log_gluten_free_generation,
)


def test_anonymize_user_id_is_deterministic():
    assert _anonymize_user_id("user-42") == _anonymize_user_id("user-42")


def test_anonymize_user_id_does_not_expose_raw_id():
    raw = "user-secret-123"
    result = _anonymize_user_id(raw)
    assert raw not in result
    assert len(result) == 16


def test_log_gluten_free_generation_emits_json(caplog):
    with caplog.at_level(logging.INFO, logger="pantrypilot.gluten_monitor"):
        log_gluten_free_generation(
            user_id="user-99",
            is_gluten_free=True,
            blocklist_hit=True,
            flagged_ingredient="soy sauce",
            retry_triggered=True,
            final_status="retry_clean",
        )

    assert len(caplog.records) == 1
    entry = json.loads(caplog.records[0].message)
    assert entry["event"] == "gluten_free_recipe_generation"
    assert entry["dietary_flag_gluten_free"] is True
    assert entry["blocklist_hit"] is True
    assert entry["flagged_ingredient"] == "soy sauce"
    assert entry["retry_triggered"] is True
    assert entry["final_status"] == "retry_clean"
    # user hash must not be the raw id
    assert entry["user_hash"] != "user-99"


def test_log_gluten_free_generation_no_blocklist_hit(caplog):
    with caplog.at_level(logging.INFO, logger="pantrypilot.gluten_monitor"):
        log_gluten_free_generation(
            user_id="user-7",
            is_gluten_free=True,
            blocklist_hit=False,
            flagged_ingredient=None,
            retry_triggered=False,
            final_status="ok",
        )

    entry = json.loads(caplog.records[0].message)
    assert entry["blocklist_hit"] is False
    assert entry["flagged_ingredient"] is None
    assert entry["retry_triggered"] is False
    assert entry["final_status"] == "ok"


def test_log_non_gluten_free_request_still_emits(caplog):
    """Non-gluten-free requests should be loggable to serve as baseline."""
    with caplog.at_level(logging.INFO, logger="pantrypilot.gluten_monitor"):
        log_gluten_free_generation(
            user_id="user-1",
            is_gluten_free=False,
            blocklist_hit=False,
            flagged_ingredient=None,
            retry_triggered=False,
            final_status="ok",
        )

    entry = json.loads(caplog.records[0].message)
    assert entry["dietary_flag_gluten_free"] is False


def test_log_violation_after_retry(caplog):
    with caplog.at_level(logging.INFO, logger="pantrypilot.gluten_monitor"):
        log_gluten_free_generation(
            user_id="user-55",
            is_gluten_free=True,
            blocklist_hit=True,
            flagged_ingredient="wheat starch",
            retry_triggered=True,
            final_status="violation_after_retry",
        )

    entry = json.loads(caplog.records[0].message)
    assert entry["final_status"] == "violation_after_retry"
    assert entry["flagged_ingredient"] == "wheat starch"
