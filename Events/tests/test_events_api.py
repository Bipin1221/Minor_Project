from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Events, Category, Comment, Rating, Interest
from datetime import date, time
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

class EventsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'testuser@example.com',
            'testpass123',
            role='organizer'
        )
        self.client.force_authenticate(self.user)
        
        self.category = Category.objects.create(name='Test Category', user=self.user)
        self.event = Events.objects.create(
            user=self.user,
            title='Test Event',
            event_dates=date(2025, 2, 14),
            time_start=time(14, 30, 00),
            link='https://testevent.com',
            description='Test description'
        )
        self.event.category.add(self.category)

    def test_create_event(self):
        """Test creating an event"""
        payload = {
            'title': 'New Test Event',
            'event_dates': '2025-02-15',
            'time_start': '15:30:00',
            'link': 'https://newtestevent.com',
            'description': 'New test description',
            'category': [{'name': 'New Category'}]
        }
        res = self.client.post(reverse('events-list'), payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        event = Events.objects.get(id=res.data['id'])
        self.assertEqual(event.title, payload['title'])

    def test_retrieve_events(self):
        """Test retrieving a list of events"""
        res = self.client.get(reverse('events-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_update_event(self):
        """Test updating an event"""
        payload = {'title': 'Updated Event Title'}
        url = reverse('events-detail', args=[self.event.id])
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, payload['title'])

    def test_delete_event(self):
        """Test deleting an event"""
        url = reverse('events-detail', args=[self.event.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Events.objects.filter(id=self.event.id).exists())

    def test_public_events_list(self):
        """Test retrieving public events list"""
        res = self.client.get(reverse('public-events-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_public_event_detail(self):
        """Test retrieving public event detail"""
        url = reverse('public-events-detail', args=[self.event.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['title'], self.event.title)

    def test_create_comment(self):
        """Test creating a comment on an event"""
        self.user.role = 'attendee'
        self.user.save()
        payload = {'text': 'Great event!'}
        url = reverse('create-comment', args=[self.event.id])
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Comment.objects.filter(event=self.event, text=payload['text']).exists())

    def test_create_rating(self):
        """Test creating a rating for an event"""
        self.user.role = 'attendee'
        self.user.save()
        payload = {'value': 5}
        url = reverse('create-rating', args=[self.event.id])
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Rating.objects.filter(event=self.event, value=payload['value']).exists())

    def test_show_interest(self):
        """Test showing interest in an event"""
        self.user.role = 'attendee'
        self.user.save()
        url = reverse('show-interest', args=[self.event.id])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Interest.objects.filter(event=self.event, user=self.user).exists())

    def test_upload_event_image(self):
        """Test uploading an image for an event"""
        url = reverse('event-upload-image', args=[self.event.id])
        image = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        res = self.client.post(url, {'image': image}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertIsNotNone(self.event.image)

   

    def test_search_events(self):
        """Test searching events"""
        url = f"{reverse('events-list')}?search=Test"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['title'], 'Test Event')

 