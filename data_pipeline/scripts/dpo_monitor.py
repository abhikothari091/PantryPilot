import os
import requests
from sqlalchemy import create_engine, text
from scripts.config import DB_URL

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

# Function to send Slack notification
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
    count = check_new_pairs()
    if count >= 50:
        send_slack_alert(count)
    else:
        print(f"[DPO Monitor] Count {count} is below threshold (50). No action taken.")
