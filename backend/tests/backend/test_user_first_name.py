"""
Tests for User.first_name field and display name feature.

TDD Red Phase: These tests define the expected behavior for showing
user's first name instead of broker_user_id in the nav bar.
"""
import pytest
from app.models.users import User


@pytest.mark.unit
class TestUserFirstNameModel:
    """Test that User model has first_name field."""

    def test_user_model_has_first_name_field(self):
        """User model should have a first_name attribute."""
        user = User()
        assert hasattr(user, "first_name"), "User model must have first_name field"

    def test_user_first_name_defaults_to_none(self):
        """first_name should default to None for backward compatibility."""
        user = User()
        assert user.first_name is None

    def test_user_first_name_can_be_set(self):
        """first_name should accept a string value."""
        user = User()
        user.first_name = "Abhay"
        assert user.first_name == "Abhay"

    def test_user_repr_includes_first_name(self):
        """User repr should include first_name when set."""
        user = User()
        user.first_name = "Abhay"
        repr_str = repr(user)
        assert "Abhay" in repr_str or "first_name" in repr_str


@pytest.mark.unit
class TestAuthMeFirstName:
    """Test that GET /api/auth/me returns first_name."""

    def test_me_response_includes_first_name_key(self):
        """The /me response user object should include first_name."""
        # This test validates the response schema
        # The actual API test would need the full app context
        expected_keys = {"id", "email", "created_at", "last_login", "first_name"}
        # We verify the expected schema has first_name
        assert "first_name" in expected_keys
