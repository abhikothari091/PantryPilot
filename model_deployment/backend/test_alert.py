import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add backend directory to sys.path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from models import Base, User, RecipePreference, RecipeHistory
from services.notification_service import check_and_notify_threshold

# 1. Setup: In-memory SQLite database
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def run_alert_test():
    """
    Simulates the conditions to trigger a Slack alert for low satisfaction ratio.
    """
    db = SessionLocal()
    print("🚀 Starting alert test...")

    # 2. Create a test user
    test_user = User(
        id=1,
        username="test_user",
        email="test@example.com",
        hashed_password="abc",
        created_at=datetime.utcnow()
    )
    db.add(test_user)
    db.commit()
    print(f"👤 Created user '{test_user.username}' (ID: {test_user.id})")

    # 3. Create dummy data to meet thresholds
    preference_count = 50
    feedback_count = 50
    
    # Target satisfaction: 60% (30 likes / 50 total)
    likes = 30
    dislikes = feedback_count - likes
    
    print(f"📊 Simulating data: {preference_count} preferences, {feedback_count} feedbacks ({likes} likes, {dislikes} dislikes)")

    # Create RecipePreference entries
    for i in range(preference_count):
        pref = RecipePreference(
            user_id=test_user.id,
            prompt=f"prompt_{i}",
            variant_a={"recipe": "A"},
            variant_b={"recipe": "B"},
            chosen_variant="A",
            skipped=False
        )
        db.add(pref)

    # Create RecipeHistory entries with feedback
    for i in range(feedback_count):
        score = 2 if i < likes else 1  # First 30 are likes, rest are dislikes
        history = RecipeHistory(
            user_id=test_user.id,
            recipe_json={"recipe": f"history_{i}"},
            feedback_score=score
        )
        db.add(history)
    
    db.commit()
    print("✅ Dummy data created successfully.")

    # 4. Calculate counts and ratio from the dummy data
    total_preferences = db.query(RecipePreference).filter(
        RecipePreference.user_id == test_user.id,
        RecipePreference.skipped == False
    ).count()

    total_with_feedback = db.query(RecipeHistory).filter(
        RecipeHistory.user_id == test_user.id,
        RecipeHistory.feedback_score > 0
    ).count()
    
    liked_count = db.query(RecipeHistory).filter(
        RecipeHistory.user_id == test_user.id,
        RecipeHistory.feedback_score == 2
    ).count()

    satisfaction_ratio = liked_count / total_with_feedback if total_with_feedback > 0 else 1.0

    print("\n" + "="*30)
    print("📋 PRE-CHECK CONDITIONS")
    print(f"Preference Count: {total_preferences} (Threshold: 50)")
    print(f"Feedback Count:   {total_with_feedback} (Threshold: 50)")
    print(f"Satisfaction:     {satisfaction_ratio:.1%} (Threshold: < 70%)")
    print("="*30 + "\n")

    # 5. Execute the function to be tested
    print("📢 Calling 'check_and_notify_threshold'...")
    
    # Ensure SLACK_WEBHOOK_URL is not set, so it prints to console
    if 'SLACK_WEBHOOK_URL' in os.environ:
        del os.environ['SLACK_WEBHOOK_URL']
        print("🔧 Temporarily removed SLACK_WEBHOOK_URL to force console output.")

    # Call the function
    sent = check_and_notify_threshold(
        user_id=test_user.id,
        username=test_user.username,
        preference_count=total_preferences,
        satisfaction_ratio=satisfaction_ratio,
        feedback_count=total_with_feedback,
        db=db,
        base_url="http://fake-test-url.com"
    )
    
    print("\n" + "="*30)
    print("🏁 TEST RESULT")
    if sent is True or (sent is False and "SLACK_WEBHOOK_URL not configured" in sys.stdout.getvalue()):
        print("✅ SUCCESS: Alert was triggered as expected.")
    elif sent is None:
        print("❌ FAILURE: Alert was NOT triggered. Thresholds were likely not met.")
    else:
        print("❓ UNKNOWN: The function returned an unexpected value.")
    print("="*30)

    db.close()

if __name__ == "__main__":
    # Use a simple way to capture stdout for verification
    from io import StringIO
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    run_alert_test()

    sys.stdout = old_stdout
    output = captured_output.getvalue()
    print(output)

    if "[ALERT] SLACK_WEBHOOK_URL not configured" in output:
         print("\n🎉 Test Passed: The alert logic was correctly triggered.")
    else:
         print("\n🔥 Test Failed: The alert logic was not triggered.")
