import pytest
from django.urls import reverse


SIGNUP_URL = reverse('auth-signup')
TOKEN_URL = reverse('auth-token')
REFRESH_URL = reverse('auth-token-refresh')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def signup(client, email='user@test.com', password='strongpass123', role='user'):
    return client.post(SIGNUP_URL, {'email': email, 'password': password, 'role': role}, content_type='application/json')


def login(client, email='user@test.com', password='strongpass123'):
    return client.post(TOKEN_URL, {'email': email, 'password': password}, content_type='application/json')


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSignup:
    def test_signup_success(self, client):
        res = signup(client)
        assert res.status_code == 201
        assert res.json()['email'] == 'user@test.com'
        assert res.json()['role'] == 'user'
        assert 'password' not in res.json()

    def test_signup_duplicate_email(self, client):
        signup(client)
        res = signup(client)
        assert res.status_code == 400
        assert 'email' in res.json()

    def test_signup_missing_email(self, client):
        res = client.post(SIGNUP_URL, {'password': 'strongpass123'}, content_type='application/json')
        assert res.status_code == 400

    def test_signup_missing_password(self, client):
        res = client.post(SIGNUP_URL, {'email': 'user@test.com'}, content_type='application/json')
        assert res.status_code == 400

    def test_signup_password_too_short(self, client):
        res = signup(client, password='123')
        assert res.status_code == 400

    def test_signup_invalid_email(self, client):
        res = signup(client, email='not-an-email')
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, client):
        signup(client)
        res = login(client)
        assert res.status_code == 200
        data = res.json()
        assert 'access' in data
        assert 'refresh' in data

    def test_login_wrong_password(self, client):
        signup(client)
        res = login(client, password='wrongpass')
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        res = login(client)
        assert res.status_code == 401

    def test_login_missing_fields(self, client):
        res = client.post(TOKEN_URL, {'email': 'user@test.com'}, content_type='application/json')
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_success(self, client):
        signup(client)
        refresh_token = login(client).json()['refresh']
        res = client.post(REFRESH_URL, {'refresh': refresh_token}, content_type='application/json')
        assert res.status_code == 200
        assert 'access' in res.json()

    def test_refresh_invalid_token(self, client):
        res = client.post(REFRESH_URL, {'refresh': 'invalid.token.here'}, content_type='application/json')
        assert res.status_code == 401

    def test_refresh_missing_token(self, client):
        res = client.post(REFRESH_URL, {}, content_type='application/json')
        assert res.status_code == 400
