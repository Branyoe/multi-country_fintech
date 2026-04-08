import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

LIST_URL   = reverse('applications-list')
DETAIL_URL = lambda pk: reverse('applications-detail', args=[pk])

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(email='applicant@test.com', password='pass1234')

@pytest.fixture
def other_user(db):
    return User.objects.create_user(email='other@test.com', password='pass1234')

def _make_auth_client(email, password):
    c = Client()
    res = c.post(
        reverse('auth-token'),
        {'email': email, 'password': password},
        content_type='application/json',
    )
    token = res.json()['access']
    c.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return c

@pytest.fixture
def auth_client(user):
    return _make_auth_client('applicant@test.com', 'pass1234')

@pytest.fixture
def other_auth_client(other_user):
    return _make_auth_client('other@test.com', 'pass1234')

def payload(**kwargs):
    base = {
        'country':          'MX',
        'full_name':        'Juan Pérez',
        'document_type':    'CURP',
        'document_number':  'PERJ800101HDFRZN09',
        'amount_requested': '50000.00',
        'monthly_income':   '15000.00',
    }
    base.update(kwargs)
    return base

# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuth:
    def test_unauthenticated_list_returns_401(self, client):
        res = client.get(LIST_URL)
        assert res.status_code == 401

    def test_unauthenticated_create_returns_401(self, client):
        res = client.post(LIST_URL, payload(), content_type='application/json')
        assert res.status_code == 401

# ---------------------------------------------------------------------------
# Crear solicitud
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCreate:
    def test_create_success(self, auth_client):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.status_code == 201
        data = res.json()
        assert data['country'] == 'MX'
        assert data['status'] == 'pending'
        assert data['full_name'] == 'Juan Pérez'
        assert 'id' in data

    def test_create_sets_status_pending(self, auth_client):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.json()['status'] == 'pending'

    def test_create_wrong_document_type_for_country(self, auth_client):
        res = auth_client.post(LIST_URL, payload(country='ES', document_type='CURP'), content_type='application/json')
        assert res.status_code == 400
        assert 'document_type' in res.json()

    def test_create_correct_document_per_country(self, auth_client):
        cases = [
            ('ES', 'DNI'),
            ('PT', 'NIF'),
            ('IT', 'CODICE_FISCALE'),
            ('MX', 'CURP'),
            ('CO', 'CC'),
            ('BR', 'CPF'),
        ]
        for country, doc_type in cases:
            res = auth_client.post(LIST_URL, payload(country=country, document_type=doc_type), content_type='application/json')
            assert res.status_code == 201, f'{country} failed with {res.json()}'

    def test_create_missing_required_field(self, auth_client):
        data = payload()
        del data['full_name']
        res = auth_client.post(LIST_URL, data, content_type='application/json')
        assert res.status_code == 400

    def test_create_invalid_country(self, auth_client):
        res = auth_client.post(LIST_URL, payload(country='XX'), content_type='application/json')
        assert res.status_code == 400

    def test_create_negative_amount(self, auth_client):
        res = auth_client.post(LIST_URL, payload(amount_requested='-100'), content_type='application/json')
        assert res.status_code == 400

# ---------------------------------------------------------------------------
# Listar solicitudes
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestList:
    def test_list_returns_only_own_applications(self, auth_client, other_auth_client):
        auth_client.post(LIST_URL, payload(country='MX', document_type='CURP'), content_type='application/json')
        auth_client.post(LIST_URL, payload(country='CO', document_type='CC'), content_type='application/json')
        other_auth_client.post(LIST_URL, payload(country='BR', document_type='CPF'), content_type='application/json')

        res = auth_client.get(LIST_URL)
        assert res.status_code == 200
        assert res.json()['count'] == 2

    def test_list_filter_by_country(self, auth_client):
        auth_client.post(LIST_URL, payload(country='MX', document_type='CURP'), content_type='application/json')
        auth_client.post(LIST_URL, payload(country='CO', document_type='CC'), content_type='application/json')

        res = auth_client.get(LIST_URL + '?country=MX')
        assert res.status_code == 200
        results = res.json()['results']
        assert len(results) == 1
        assert results[0]['country'] == 'MX'

    def test_list_filter_country_case_insensitive(self, auth_client):
        auth_client.post(LIST_URL, payload(country='BR', document_type='CPF'), content_type='application/json')
        res = auth_client.get(LIST_URL + '?country=br')
        assert res.status_code == 200
        assert len(res.json()['results']) == 1

    def test_list_empty_for_new_user(self, auth_client):
        res = auth_client.get(LIST_URL)
        assert res.status_code == 200
        assert res.json()['count'] == 0

# ---------------------------------------------------------------------------
# Detalle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRetrieve:
    def test_retrieve_own_application(self, auth_client):
        create_res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        pk = create_res.json()['id']

        res = auth_client.get(DETAIL_URL(pk))
        assert res.status_code == 200
        assert res.json()['id'] == pk

    def test_retrieve_other_user_application_returns_404(self, auth_client, other_auth_client):
        create_res = other_auth_client.post(LIST_URL, payload(), content_type='application/json')
        pk = create_res.json()['id']

        res = auth_client.get(DETAIL_URL(pk))
        assert res.status_code == 404

# ---------------------------------------------------------------------------
# Actualizar estado
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStatusUpdate:
    def test_update_pending_to_under_review(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'under_review'}, content_type='application/json')
        assert res.status_code == 200
        assert res.json()['status'] == 'under_review'

    def test_update_pending_to_approved(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        assert res.status_code == 200

    def test_update_pending_to_rejected(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'rejected'}, content_type='application/json')
        assert res.status_code == 200

    def test_invalid_transition_approved_to_pending(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'pending'}, content_type='application/json')
        assert res.status_code == 400

    def test_invalid_transition_rejected_to_approved(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'rejected'}, content_type='application/json')
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        assert res.status_code == 400

    def test_cannot_put_only_patch(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        res = auth_client.put(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        assert res.status_code == 405

    def test_update_other_user_application_returns_404(self, auth_client, other_auth_client):
        pk = other_auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        assert res.status_code == 404
