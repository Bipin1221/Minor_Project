from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from rest_framework.authtoken.models import Token

# Assuming you have a user create URL
CREATE_USER_URL = reverse('user:sign-up')
# Assuming you have a login URL
TOKEN_URL = reverse('user:login')
# Assuming you have a manage user URL
ME_URL = reverse('user:profile')
VERIFY_TOKEN_URL = reverse('user:verify-login')  # Replace with your actual URL name


def create_user(**params):
    """Helper function to create new user"""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the users API (public)"""

    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_success_with_role(self):
        """Test creating user with valid payload and role is successful"""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
            'role': 'attendee'  # Include role in payload
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        # Check if role is set
        self.assertEqual(user.role, payload['role'])
        self.assertNotIn('password', res.data)

    def test_user_exists(self):
        """Test creating a user that already exists fails"""
        payload = {'email': 'test@example.com',
                   'password': 'testpass123', 'role': 'attendee'}
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """Test that password must be more than 8 characters"""
        payload = {'email': 'test@example.com',
                   'password': 'pw', 'role': 'attendee'}
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    @patch('user.views.send_mail')
    def test_create_token_for_user(self, mock_send_mail):
        """Test that a token is created for the user"""
        payload = {'email': 'test@example.com', 'password': 'testpass123'}
        create_user(**payload)
        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('message', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()

    def test_create_token_invalid_credentials(self):
        """Test that token is not created if invalid credentials are given"""
        create_user(email='test@example.com', password='testpass123')
        payload = {'email': 'test@example.com', 'password': 'wrong'}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        """Test that token is not created if user doesn't exist"""
        payload = {'email': 'test@example.com', 'password': 'testpass123'}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_missing_field(self):
        """Test that email and password are required"""
        res = self.client.post(TOKEN_URL, {'email': 'one', 'password': ''})
        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test that authentication is required for users"""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """Test API requests that require authentication"""

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='testpass123',
            name='name',
            role='organizer'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in used"""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email,
            'role': self.user.role
        })

    def test_post_me_not_allowed(self):
        """Test that POST is not allowed on the me url"""
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating the user profile for authenticated user"""
        payload = {'name': 'new name', 'password': 'newpassword123'}

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_update_user_role_not_allowed(self):
        """Test that users can't modify their role through API"""
        payload = {'role': 'attendee'}
        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        # Role should not change
        self.assertEqual(self.user.role, 'organizer')
        # Response should also show original role
        self.assertEqual(res.data['role'], 'organizer')
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AdminUserApiTests(TestCase):  # New test case for admin user

    def setUp(self):
        self.admin_user = create_user(
            email='admin@example.com',
            password='adminpass123',
            name='Admin User',
            role='admin',
            is_staff=True,  # Superuser Status
            is_superuser=True  # Add Superuser Status
        )
        self.user = create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User',
            role='attendee'
        )
        self.client = APIClient()
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)


class VerifyTokenTests(TestCase):
    """Test the token verification API"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

    def test_verify_token_success(self):
        """Test successful token verification"""
        payload = {'token': self.token.key}
        res = self.client.post(VERIFY_TOKEN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['user_id'], self.user.id)

    def test_verify_token_invalid(self):
        """Test token verification with invalid token"""
        payload = {'token': 'invalidtoken'}
        res = self.client.post(VERIFY_TOKEN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
