import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

SIGNUP_URL = reverse('auth-signup')
ME_URL = reverse('auth-me')
TOKEN_URL = reverse('auth-token')


def _make_auth_client(email, password):
    c = Client()
    res = c.post(TOKEN_URL, {'email': email, 'password': password}, content_type='application/json')
    c.defaults['HTTP_AUTHORIZATION'] = f"Bearer {res.json()['access']}"
    return c


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSignup:
    def test_signup_creates_user(self):
        res = Client().post(
            SIGNUP_URL,
            {'email': 'new@test.com', 'password': 'pass1234'},
            content_type='application/json',
        )
        assert res.status_code == 201
        assert User.objects.filter(email='new@test.com').exists()

    def test_signup_always_creates_user_role(self):
        """El endpoint de signup debe crear siempre role='user'."""
        Client().post(
            SIGNUP_URL,
            {'email': 'newuser@test.com', 'password': 'pass1234'},
            content_type='application/json',
        )
        user = User.objects.get(email='newuser@test.com')
        assert user.role == 'user'

    def test_signup_ignores_admin_role_in_payload(self):
        """Aunque el cliente envíe role='admin', debe ignorarse."""
        Client().post(
            SIGNUP_URL,
            {'email': 'hacker@test.com', 'password': 'pass1234', 'role': 'admin'},
            content_type='application/json',
        )
        user = User.objects.get(email='hacker@test.com')
        assert user.role == 'user'

    def test_signup_response_does_not_include_role_field(self):
        """El serializer de signup no expone el campo role en la respuesta."""
        res = Client().post(
            SIGNUP_URL,
            {'email': 'resp@test.com', 'password': 'pass1234'},
            content_type='application/json',
        )
        assert res.status_code == 201
        assert 'role' not in res.json()

    def test_signup_requires_email(self):
        res = Client().post(SIGNUP_URL, {'password': 'pass1234'}, content_type='application/json')
        assert res.status_code == 400

    def test_signup_requires_password_min_8_chars(self):
        res = Client().post(
            SIGNUP_URL,
            {'email': 'short@test.com', 'password': '1234567'},
            content_type='application/json',
        )
        assert res.status_code == 400

    def test_signup_duplicate_email_returns_400(self):
        data = {'email': 'dup@test.com', 'password': 'pass1234'}
        Client().post(SIGNUP_URL, data, content_type='application/json')
        res = Client().post(SIGNUP_URL, data, content_type='application/json')
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# /me — perfil del usuario autenticado
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMe:
    def test_me_returns_user_data(self, db):
        User.objects.create_user(email='me@test.com', password='pass1234')
        client = _make_auth_client('me@test.com', 'pass1234')
        res = client.get(ME_URL)
        assert res.status_code == 200
        data = res.json()
        assert data['email'] == 'me@test.com'
        assert data['role'] == 'user'
        assert 'id' in data
        assert 'created_at' in data

    def test_me_returns_admin_role_for_admin(self, db):
        User.objects.create_user(email='admin@test.com', password='pass1234', role='admin')
        client = _make_auth_client('admin@test.com', 'pass1234')
        res = client.get(ME_URL)
        assert res.status_code == 200
        assert res.json()['role'] == 'admin'

    def test_me_unauthenticated_returns_401(self):
        res = Client().get(ME_URL)
        assert res.status_code == 401
