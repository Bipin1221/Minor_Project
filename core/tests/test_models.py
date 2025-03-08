"""Tests for models"""
from django.test import TestCase
from core import models
from unittest.mock import patch
from django.contrib.auth import get_user_model


def create_user(email='test@example.com', password='testpass123'):
    """Create and return a new user"""
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    """Test models"""

    def test_create_user_with_email_successful(self):
        """Test creating user with an email is successful."""
        email = 'test@example.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(email=email, password=password)
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test that the email for a new user is normalized."""
        sample_emails = [
            ['test1@EXAMPLE.COM', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['Test3@Example.COM', 'Test3@example.com'],
           
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'sample123')
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test that creating a user without an email raises an error"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test12345')

    def test_create_superuser(self):
        """Test creating a superuser"""
        user = get_user_model().objects.create_superuser('test@example.com', 'test12345')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_event(self):
        """Test creating an event is successful"""
        user = create_user()
        event = models.Events.objects.create(
            user=user,
            title="Sample Event",
            created_at='2025-02-12',
            event_dates='2025-04-03',
            time_start="00:00:00",
            description='Sample event description',
        )
        self.assertEqual(str(event), event.title)

    def test_create_category(self):
        """Test creating a category is successful"""
        user = create_user()
        category = models.Category.objects.create(user=user, name='Category1')
        self.assertEqual(str(category), category.name)

    def test_event_with_category(self):
        """Test that an event can be associated with a category"""
        user = create_user()
        category = models.Category.objects.create(user=user, name='Music')
        event = models.Events.objects.create(
            user=user,
            title="Music Festival",
            created_at='2025-02-12',
            event_dates='2025-04-03',
            time_start="00:00:00",
            description='Live music event',
        )
        event.category.add(category)
        self.assertIn(category, event.category.all())

    def test_filter_events_by_title(self):
        """Test searching events by title"""
        user = create_user()
        models.Events.objects.create(user=user, title="Tech Conference", description="Tech talk")
        models.Events.objects.create(user=user, title="Music Festival", description="Live concert")
        
        events = models.Events.objects.filter(title__icontains="Tech")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Tech Conference")

    def test_filter_events_by_category(self):
        """Test filtering events by category"""
        user = create_user()
        category_music = models.Category.objects.create(user=user, name='Music')
        category_tech = models.Category.objects.create(user=user, name='Tech')

        event1 = models.Events.objects.create(user=user, title="Music Festival")
        event2 = models.Events.objects.create(user=user, title="Tech Conference")

        event1.category.add(category_music)
        event2.category.add(category_tech)

        filtered_events = models.Events.objects.filter(category=category_music)
        self.assertEqual(len(filtered_events), 1)
        self.assertEqual(filtered_events[0].title, "Music Festival")

    def test_filter_events_by_date(self):
        """Test filtering events by date"""
        user = create_user()
        event1 = models.Events.objects.create(user=user, title="Event 1", event_dates="2025-04-01")
        event2 = models.Events.objects.create(user=user, title="Event 2", event_dates="2025-04-03")

        events = models.Events.objects.filter(event_dates="2025-04-01")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Event 1")

    def test_user_can_express_interest_in_event(self):
        """Test a user can express interest in an event"""
        user = create_user()
        event = models.Events.objects.create(user=user, title="Sample Event")

        interest = models.Interest.objects.create(user=user, event=event)
        self.assertEqual(str(interest.user), user.email)

    def test_user_cannot_express_interest_twice(self):
        """Test that a user cannot express interest in the same event twice"""
        user = create_user()
        event = models.Events.objects.create(user=user, title="Sample Event")

        models.Interest.objects.create(user=user, event=event)
        with self.assertRaises(Exception):
            models.Interest.objects.create(user=user, event=event)

    def test_user_can_rate_event(self):
        """Test a user can rate an event"""
        user = create_user()
        event = models.Events.objects.create(user=user, title="Sample Event")

        rating = models.Rating.objects.create(user=user, event=event, value=5)
        self.assertEqual(rating.value, 5)

    def test_user_cannot_rate_event_twice(self):
        """Test that a user cannot rate the same event twice"""
        user = create_user()
        event = models.Events.objects.create(user=user, title="Sample Event")

        models.Rating.objects.create(user=user, event=event, value=5)
        with self.assertRaises(Exception):
            models.Rating.objects.create(user=user, event=event, value=4)

    @patch('core.models.uuid.uuid4')
    def test_event_file_name_uuid(self, mock_uuid):
        """Test generating image path."""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.event_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f'uploads/events/{uuid}.jpg')
