"""
Notification Service for Retraining Alerts
Sends Slack alerts when users reach preference thresholds.
"""

import os
import requests
from datetime import datetime
from typing import Optional

# Configuration
PREFERENCE_THRESHOLD = 50


def send_slack_alert(
    user_id: int,
    username: str,
    preference_count: int,
    approval_url: str
) -> bool:
    """
    Send a Slack alert when a user reaches the preference threshold.
    
    Requires environment variable:
    - SLACK_WEBHOOK_URL: Slack incoming webhook URL
    
    Args:
        user_id: The user's ID
        username: The user's username
        preference_count: Current preference count
        approval_url: URL for admin to approve retraining
        
    Returns:
        True if sent successfully, False otherwise
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        print(f"[ALERT] SLACK_WEBHOOK_URL not configured.")
        print(f"[ALERT] User {username} (ID: {user_id}) reached {preference_count} preferences!")
        print(f"[ALERT] Approval URL: {approval_url}")
        return False
    
    # Slack message with blocks for rich formatting
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎯 DPO Retraining Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*User:*\n{username}"},
                    {"type": "mrkdwn", "text": f"*User ID:*\n{user_id}"},
                    {"type": "mrkdwn", "text": f"*Preferences:*\n{preference_count}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"User *{username}* has provided *{preference_count} preference choices*. "
                            f"This is enough data to retrain a personalized DPO model."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve Retraining",
                            "emoji": True
                        },
                        "style": "primary",
                        "url": approval_url
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        
        if response.status_code == 200:
            print(f"[SLACK] Alert sent for user {username} (ID: {user_id})")
            return True
        else:
            print(f"[SLACK] Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"[SLACK] Error: {e}")
        return False


def check_and_notify_threshold(
    user_id: int,
    username: str,
    preference_count: int,
    base_url: str = "http://localhost:8000"
) -> Optional[bool]:
    """
    Check if user has reached the threshold and send Slack notification.
    
    Returns:
        True if notification sent, False if failed, None if threshold not reached
    """
    if preference_count != PREFERENCE_THRESHOLD:
        return None
    
    print(f"[ALERT] User {username} (ID: {user_id}) reached {preference_count} preferences!")
    
    approval_url = f"{base_url}/training/approve/{user_id}"
    
    return send_slack_alert(
        user_id=user_id,
        username=username,
        preference_count=preference_count,
        approval_url=approval_url
    )
