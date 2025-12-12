import os
import requests
from sqlalchemy import create_engine, text
from scripts.config import DB_URL

# Threshold for approval rate alert (80%)
APPROVAL_RATE_THRESHOLD = 0.80

# Minimum number of feedback required before calculating approval rate
# (to avoid alerts on statistically insignificant sample sizes)
MIN_FEEDBACK_COUNT = 10

# Function to check for new preference pairs
def check_new_pairs():
    engine = create_engine(DB_URL)
    
    # Query to count untrained records (where exported_for_training is False or NULL)
    query = text("""
        SELECT count(*) 
        FROM recipe_preferences 
        WHERE exported_for_training IS NOT TRUE 
        AND chosen_variant IS NOT NULL
    """)
    
    with engine.begin() as connection:
        result = connection.execute(query)
        count = result.scalar()
        
    print(f"[DPO Monitor] Found {count} new preference pairs.")
    return count


def check_approval_rate(days: int = 7):
    """
    Check the approval rate (likes / (likes + dislikes)) from recipe_history
    for the last N days.
    
    Returns:
        tuple: (approval_rate, likes, dislikes) or (None, 0, 0) if no data
    """
    engine = create_engine(DB_URL)
    
    query = text("""
        SELECT 
            SUM(CASE WHEN feedback_score = 2 THEN 1 ELSE 0 END) as likes,
            SUM(CASE WHEN feedback_score = 1 THEN 1 ELSE 0 END) as dislikes
        FROM recipe_history 
        WHERE feedback_score IN (1, 2)
        AND created_at >= NOW() - make_interval(days => :days)
    """)
    
    with engine.begin() as connection:
        result = connection.execute(query, {"days": days})
        row = result.fetchone()
        
    likes = row[0] or 0
    dislikes = row[1] or 0
    total = likes + dislikes
    
    if total == 0:
        print(f"[Approval Monitor] No feedback data in the last {days} days.")
        return None, 0, 0
    
    approval_rate = likes / total
    print(f"[Approval Monitor] Last {days} days: {likes} likes, {dislikes} dislikes, rate={approval_rate:.2%}")
    return approval_rate, likes, dislikes


def send_low_approval_alert(approval_rate: float, likes: int, dislikes: int, days: int = 7):
    """Send Slack alert when approval rate drops below threshold."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[Warning] SLACK_WEBHOOK_URL not set. Skipping alert.")
        return

    message = {
        "text": (
            f"⚠️ *PantryPilot Low Approval Rate Alert* ⚠️\n\n"
            f"Approval rate has dropped below {APPROVAL_RATE_THRESHOLD:.0%}!\n\n"
            f"📊 *Stats (Last {days} days):*\n"
            f"• 👍 Likes: {likes}\n"
            f"• 👎 Dislikes: {dislikes}\n"
            f"• 📉 Approval Rate: *{approval_rate:.1%}* (threshold: {APPROVAL_RATE_THRESHOLD:.0%})\n\n"
            f"🔍 *Recommended Actions:*\n"
            f"1. Review recent model outputs for quality issues\n"
            f"2. Check for bias in specific cuisines or preferences\n"
            f"3. Consider triggering DPO retraining with recent feedback"
        )
    }
    
    response = requests.post(webhook_url, json=message)
    if response.status_code == 200:
        print("[Approval Monitor] Slack alert sent successfully.")
    else:
        print(f"[Error] Failed to send Slack alert: {response.status_code} {response.text}")


# Function to send Slack notification for DPO training
def send_slack_alert(count):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[Warning] SLACK_WEBHOOK_URL not set. Skipping alert.")
        return

    message = {
        "text": f"🚨 *PantryPilot DPO Alert* 🚨\n\nFound *{count}* new preference pairs ready for training!\n\nRun the following command to start retraining:\n`python model_development/training_pipeline/05_dpo_training/scripts/auto_retrain_pipeline.py`"
    }
    
    response = requests.post(webhook_url, json=message)
    if response.status_code == 200:
        print("[DPO Monitor] Slack alert sent successfully.")
    else:
        print(f"[Error] Failed to send Slack alert: {response.status_code} {response.text}")


if __name__ == "__main__":
    # Check for new preference pairs (DPO training trigger)
    count = check_new_pairs()
    if count >= 50:
        send_slack_alert(count)
    else:
        print(f"[DPO Monitor] Count {count} is below threshold (50). No action taken.")
    
    # Check approval rate (quality monitoring)
    approval_rate, likes, dislikes = check_approval_rate(days=7)
    total_feedback = likes + dislikes
    
    if total_feedback < MIN_FEEDBACK_COUNT:
        print(f"[Approval Monitor] Only {total_feedback} feedback (minimum: {MIN_FEEDBACK_COUNT}). Skipping approval rate check.")
    elif approval_rate is not None and approval_rate < APPROVAL_RATE_THRESHOLD:
        send_low_approval_alert(approval_rate, likes, dislikes, days=7)
    elif approval_rate is not None:
        print(f"[Approval Monitor] Approval rate {approval_rate:.1%} is above threshold. No alert needed.")
