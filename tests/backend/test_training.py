"""
Tests for training router and notification service.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock
from models import User, RecipePreference
from auth_utils import get_password_hash, create_access_token


def test_pending_retraining_requires_admin(client: TestClient, test_user, auth_headers):
    """Non-admin users cannot access pending retraining list."""
    response = client.get("/training/pending", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_pending_retraining_as_admin(client: TestClient, test_db: Session):
    """Admin can view pending retraining requests."""
    # Create admin user
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass")
    )
    test_db.add(admin)
    test_db.commit()
    
    token = create_access_token(data={"sub": "admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/training/pending", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "threshold" in data
    assert "pending_count" in data
    assert "users" in data


def test_approve_retraining_user_not_found(client: TestClient, test_db: Session):
    """Approve retraining fails for non-existent user."""
    response = client.post("/training/approve/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_approve_retraining_insufficient_preferences(client: TestClient, test_db: Session):
    """Approve retraining fails when user has less than 50 preferences."""
    # Create user
    user = User(
        username="lowpref_user",
        email="lowpref@example.com",
        hashed_password=get_password_hash("pass123")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    response = client.post(f"/training/approve/{user.id}")
    assert response.status_code == 400
    assert "Minimum 50 required" in response.json()["detail"]


def test_export_requires_admin(client: TestClient, test_user, auth_headers):
    """Non-admin users cannot export preferences."""
    response = client.get(f"/training/export/{test_user.id}", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_export_user_not_found(client: TestClient, test_db: Session):
    """Export fails for non-existent user."""
    # Create admin
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass")
    )
    test_db.add(admin)
    test_db.commit()
    
    token = create_access_token(data={"sub": "admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/training/export/99999", headers=headers)
    assert response.status_code == 404


def test_export_preferences_success(client: TestClient, test_db: Session):
    """Admin can export user preferences."""
    # Create admin
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass")
    )
    test_db.add(admin)
    test_db.commit()
    
    # Create regular user
    user = User(
        username="exportable_user",
        email="export@example.com",
        hashed_password=get_password_hash("pass123")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    token = create_access_token(data={"sub": "admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(f"/training/export/{user.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id
    assert data["username"] == "exportable_user"
    assert "dpo_pairs" in data


# Notification service tests
def test_notification_service_no_webhook():
    """Notification logs alert when webhook not configured."""
    from services.notification_service import send_slack_alert
    
    with patch.dict('os.environ', {}, clear=True):
        result = send_slack_alert(
            user_id=1,
            username="testuser",
            preference_count=50,
            approval_url="http://test.com/approve/1"
        )
    
    assert result == False


def test_notification_threshold_not_reached():
    """No notification sent if threshold not reached."""
    from services.notification_service import check_and_notify_threshold
    
    result = check_and_notify_threshold(
        user_id=1,
        username="testuser",
        preference_count=49,
        base_url="http://localhost:8000"
    )
    
    assert result is None


def test_notification_threshold_reached():
    """Notification triggered when threshold reached."""
    from services.notification_service import check_and_notify_threshold
    
    with patch('services.notification_service.send_slack_alert') as mock_send:
        mock_send.return_value = True
        
        result = check_and_notify_threshold(
            user_id=1,
            username="testuser",
            preference_count=50,
            base_url="http://localhost:8000"
        )
    
    assert result == True
    mock_send.assert_called_once()


def test_slack_alert_success():
    """Slack alert sends successfully with webhook configured."""
    from services.notification_service import send_slack_alert
    
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'}):
            result = send_slack_alert(
                user_id=1,
                username="testuser",
                preference_count=50,
                approval_url="http://test.com/approve/1"
            )
    
    assert result == True
    mock_post.assert_called_once()
