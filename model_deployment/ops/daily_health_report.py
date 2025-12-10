"""
Daily health/metrics Slack reporter.

What it does:
- Calls backend /healthz and /metrics endpoints.
- Posts a summary to Slack via SLACK_WEBHOOK_URL (same env used by DPO alerts).

Usage (cron or CI):
    export BACKEND_URL=https://your-backend
    export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
    python model_deployment/ops/daily_health_report.py
"""

import os
import sys
import datetime
import time
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
TIMEOUT = float(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))
RETRY_COUNT = int(os.getenv("HEALTH_CHECK_RETRIES", "2"))
RETRY_SLEEP = float(os.getenv("HEALTH_CHECK_RETRY_SLEEP", "2"))


def with_retry(func):
    def wrapper(*args, **kwargs):
        last_err = None
        for _ in range(RETRY_COUNT + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_err = e
                time.sleep(RETRY_SLEEP)
        # If still failing, raise the last error
        raise last_err
    return wrapper


@with_retry
def fetch_health():
    r = requests.get(f"{BACKEND_URL}/healthz", timeout=TIMEOUT)
    return True, r.status_code, r.json()


def fetch_health_safe():
    try:
        return fetch_health()
    except Exception as e:
        return False, None, {"error": str(e)}


@with_retry
def fetch_metrics_get():
    r = requests.get(f"{BACKEND_URL}/metrics", timeout=TIMEOUT, stream=True)
    return True, r.status_code, None


def fetch_metrics_safe():
    try:
        return fetch_metrics_get()
    except Exception as e:
        return False, None, str(e)


def send_slack(message: str):
    if not SLACK_WEBHOOK_URL:
        print("[WARN] SLACK_WEBHOOK_URL not set; skipping Slack send.")
        print(message)
        return
    resp = requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=5)
    if resp.status_code >= 300:
        print(f"[WARN] Slack send failed: {resp.status_code} {resp.text}")


def main():
    ok_health, status_health, body_health = fetch_health_safe()
    ok_metrics, status_metrics, err_metrics = fetch_metrics_safe()

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status_line = f"*PantryPilot Daily Health* ({ts})"

    health_line = f"- /healthz: {'OK' if ok_health else 'FAIL'} (status={status_health})"
    db_line = ""
    if isinstance(body_health, dict):
        db_line = f"  • db: {body_health.get('db')} (latency_ms={body_health.get('db_latency_ms')})"
    metrics_line = f"- /metrics: {'OK' if ok_metrics else 'FAIL'} (status={status_metrics}, err={'' if ok_metrics else err_metrics})"

    message = "\n".join([status_line, health_line, db_line, metrics_line])
    send_slack(message)


if __name__ == "__main__":
    sys.exit(main())
