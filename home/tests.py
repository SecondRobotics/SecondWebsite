import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from home.models import Staff, HistoricEvent


@pytest.mark.django_db
class TestStaffModel:
    @pytest.fixture
    def staff_member(self):
        return Staff.objects.create(
            name="John Doe",
            title="Senior Developer",
            image_url="https://example.com/image.jpg",
            bio="A talented developer with years of experience.",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            github_url="https://github.com/johndoe"
        )

    def test_staff_creation(self, staff_member):
        """Test that a staff member can be created with all fields"""
        assert staff_member.name == "John Doe"
        assert staff_member.title == "Senior Developer"
        assert staff_member.image_url == "https://example.com/image.jpg"
        assert staff_member.email == "john@example.com"

    def test_staff_string_representation(self, staff_member):
        """Test the string representation of Staff model"""
        assert str(staff_member) == "John Doe"

    def test_optional_fields(self):
        """Test that linkedin_url and github_url are optional"""
        staff_without_socials = Staff.objects.create(
            name="Jane Doe",
            title="Developer",
            image_url="https://example.com/image2.jpg",
            bio="Another talented developer.",
            email="jane@example.com"
        )
        assert staff_without_socials.linkedin_url is None
        assert staff_without_socials.github_url is None

    def test_invalid_email(self):
        """Test that invalid email raises validation error"""
        with pytest.raises(ValidationError):
            staff = Staff.objects.create(
                name="Invalid Email",
                title="Developer",
                image_url="https://example.com/image.jpg",
                bio="Test bio",
                email="invalid-email"
            )
            staff.full_clean()


@pytest.mark.django_db
class TestHistoricEventModel:
    @pytest.fixture
    def event(self):
        return HistoricEvent.objects.create(
            name="Championship 2023",
            date=date(2023, 12, 25),
            youtube_url="https://youtube.com/watch?v=123",
            first_place="Team Alpha",
            second_place="Team Beta"
        )

    def test_event_creation(self, event):
        """Test that an event can be created with all fields"""
        assert event.name == "Championship 2023"
        assert event.date == date(2023, 12, 25)
        assert event.first_place == "Team Alpha"
        assert event.second_place == "Team Beta"

    def test_event_string_representation(self, event):
        """Test the string representation of HistoricEvent model"""
        assert str(event) == "Championship 2023"

    def test_optional_fields(self):
        """Test that youtube_url and second_place are optional"""
        event_minimal = HistoricEvent.objects.create(
            name="Mini Tournament",
            date=date(2023, 1, 1),
            first_place="Winner Team"
        )
        assert event_minimal.youtube_url is None
        assert event_minimal.second_place is None

    @pytest.mark.parametrize("test_date,expected", [
        (date(2024, 12, 25), 2024),
        (date(2023, 1, 1), 2023),
        (date(2025, 6, 15), 2025),
    ])
    def test_date_validation(self, test_date, expected):
        """Test that the date field accepts valid dates"""
        event = HistoricEvent.objects.create(
            name="Test Championship",
            date=test_date,
            first_place="TBD"
        )
        assert event.date.year == expected
