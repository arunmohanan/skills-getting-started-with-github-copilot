"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

# Create test client
client = TestClient(app)


class TestHelpers:
    """Test helper functions"""
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset activities before each test"""
        # Get fresh activities
        response = client.get("/activities")
        assert response.status_code == 200


class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root_redirect(self):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Test /activities endpoint"""
    
    def test_get_activities(self):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert "Chess Club" in activities
        assert "Programming Class" in activities
        assert "Gym Class" in activities
    
    def test_activity_structure(self):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupEndpoint:
    """Test /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self):
        """Test successful signup"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "message" in result
        assert "test@mergington.edu" in result["message"]
        assert "Chess Club" in result["message"]
    
    def test_signup_adds_participant(self):
        """Test that signup actually adds participant"""
        email = "newstudent@mergington.edu"
        
        # Signup
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        activities = client.get("/activities").json()
        assert email in activities["Chess Club"]["participants"]
    
    def test_signup_duplicate_fails(self):
        """Test that duplicate signup fails"""
        # First signup
        response1 = client.post(
            "/activities/Chess%20Club/signup?email=duplicate@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Duplicate signup should fail
        response2 = client.post(
            "/activities/Chess%20Club/signup?email=duplicate@mergington.edu"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity(self):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Fake%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_signup_full_activity(self):
        """Test signup for full activity"""
        # Create an activity with only 1 spot
        activities = client.get("/activities").json()
        
        # Try to signup multiple students to fill up an activity
        activity_name = "Tennis Club"
        max_participants = activities[activity_name]["max_participants"]
        current_count = len(activities[activity_name]["participants"])
        
        # Add students until full
        for i in range(max_participants - current_count):
            email = f"student{i}@mergington.edu"
            response = client.post(
                f"/activities/Tennis%20Club/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Next signup should fail
        response = client.post(
            "/activities/Tennis%20Club/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 400
        assert "exceeded" in response.json()["detail"].lower() or "max" in response.json()["detail"].lower()


class TestUnregisterEndpoint:
    """Test /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self):
        """Test successful unregister"""
        email = "unreg@mergington.edu"
        
        # First signup
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        # Then unregister
        response = client.post(
            f"/activities/Chess%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "message" in result
        assert email in result["message"]
    
    def test_unregister_removes_participant(self):
        """Test that unregister actually removes participant"""
        email = "remove@mergington.edu"
        
        # Signup
        client.post(f"/activities/Programming%20Class/signup?email={email}")
        
        # Verify participant was added
        activities = client.get("/activities").json()
        assert email in activities["Programming Class"]["participants"]
        
        # Unregister
        client.post(f"/activities/Programming%20Class/unregister?email={email}")
        
        # Verify participant was removed
        activities = client.get("/activities").json()
        assert email not in activities["Programming Class"]["participants"]
    
    def test_unregister_not_signed_up(self):
        """Test unregister fails for non-registered student"""
        response = client.post(
            "/activities/Debate%20Team/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_nonexistent_activity(self):
        """Test unregister for non-existent activity"""
        response = client.post(
            "/activities/Fake%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestIntegration:
    """Integration tests"""
    
    def test_full_signup_unregister_cycle(self):
        """Test complete signup and unregister cycle"""
        email = "integration@mergington.edu"
        activity = "Drama Club"
        
        # Signup
        response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify participant added
        activities = client.get("/activities").json()
        count_after_signup = len(activities[activity]["participants"])
        assert email in activities[activity]["participants"]
        
        # Unregister
        response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}"
        )
        assert response.status_code == 200
        
        # Verify participant removed
        activities = client.get("/activities").json()
        count_after_unregister = len(activities[activity]["participants"])
        assert email not in activities[activity]["participants"]
        assert count_after_unregister == count_after_signup - 1
    
    def test_multiple_participants(self):
        """Test multiple participants in same activity"""
        activity = "Science Club"
        emails = ["participant1@mergington.edu", "participant2@mergington.edu", "participant3@mergington.edu"]
        
        # Signup all
        for email in emails:
            response = client.post(
                f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all added
        activities = client.get("/activities").json()
        for email in emails:
            assert email in activities[activity]["participants"]
        
        # Unregister one
        client.post(
            f"/activities/{activity.replace(' ', '%20')}/unregister?email={emails[0]}"
        )
        
        # Verify correct one removed
        activities = client.get("/activities").json()
        assert emails[0] not in activities[activity]["participants"]
        assert emails[1] in activities[activity]["participants"]
        assert emails[2] in activities[activity]["participants"]
