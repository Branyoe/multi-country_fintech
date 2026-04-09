import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from applications.models import ApplicationStatusHistory, BankProviderData, CountryValidation

User = get_user_model()

LIST_URL   = reverse('applications-list')
DETAIL_URL = lambda pk: reverse('applications-detail', args=[pk])


# ---------------------------------------------------------------------------
# Helpers de payload
# ---------------------------------------------------------------------------

def payload(**kwargs):
    """Payload válido para México (CURP)."""
    base = {
        'country':          'MX',
        'full_name':        'Juan Pérez',
        'document_number':  'PERJ800101HDFRZN09',
        'amount_requested': '50000.00',
        'monthly_income':   '15000.00',
    }
    base.update(kwargs)
    return base


def co_payload(**kwargs):
    """Payload válido para Colombia (CC)."""
    base = {
        'country':          'CO',
        'full_name':        'María García',
        'document_number':  '1234567890',
        'amount_requested': '5000.00',
        'monthly_income':   '10000.00',
    }
    base.update(kwargs)
    return base


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

@pytest.fixture(autouse=True)
def mock_celery_task(monkeypatch):
    """Evita que el task Celery se ejecute durante los tests."""
    from unittest.mock import MagicMock
    import applications.tasks as tasks_module
    mock = MagicMock()
    monkeypatch.setattr(tasks_module.process_application, 'delay', mock)
    return mock


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
    def test_create_mx_success(self, auth_client, mock_celery_task):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.status_code == 201
        data = res.json()
        assert data['country'] == 'MX'
        assert data['status'] == 'pending'
        assert data['document_type'] == 'CURP'
        assert 'id' in data
        mock_celery_task.assert_called_once()

    def test_create_co_success(self, auth_client):
        res = auth_client.post(LIST_URL, co_payload(), content_type='application/json')
        assert res.status_code == 201
        data = res.json()
        assert data['country'] == 'CO'
        assert data['document_type'] == 'CC'

    def test_create_sets_status_pending(self, auth_client):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.json()['status'] == 'pending'

    def test_create_document_type_set_by_service(self, auth_client):
        """El cliente no envía document_type — lo fija el service."""
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.status_code == 201
        assert res.json()['document_type'] == 'CURP'

    def test_create_missing_required_field(self, auth_client):
        data = payload()
        del data['full_name']
        res = auth_client.post(LIST_URL, data, content_type='application/json')
        assert res.status_code == 400

    def test_create_negative_amount(self, auth_client):
        res = auth_client.post(LIST_URL, payload(amount_requested='-100'), content_type='application/json')
        assert res.status_code == 400

    def test_create_invalid_country_choice(self, auth_client):
        """País fuera del enum Django → 400 del serializer."""
        res = auth_client.post(LIST_URL, payload(country='XX'), content_type='application/json')
        assert res.status_code == 400

    def test_unsupported_country_returns_400(self, auth_client):
        """Países válidos en el enum pero sin validator → 400 del service."""
        for country in ['ES', 'PT', 'IT', 'BR']:
            res = auth_client.post(LIST_URL, payload(country=country), content_type='application/json')
            assert res.status_code == 400, f'{country} debería retornar 400'

    def test_create_persists_bank_provider_data(self, auth_client):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        app_id = res.json()['id']
        assert BankProviderData.objects.filter(application_id=app_id).exists()
        bank = BankProviderData.objects.get(application_id=app_id)
        assert bank.provider_name == 'CNBV_MX'

    def test_create_persists_country_validations(self, auth_client):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        app_id = res.json()['id']
        rules = list(CountryValidation.objects.filter(application_id=app_id).values_list('rule_name', flat=True))
        assert 'curp_format' in rules
        assert 'monto_5x_ingreso' in rules


# ---------------------------------------------------------------------------
# Validación de documentos y reglas financieras
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestValidation:
    def test_invalid_curp_returns_422(self, auth_client):
        res = auth_client.post(LIST_URL, payload(document_number='INVALIDO'), content_type='application/json')
        assert res.status_code == 422

    def test_invalid_cc_returns_422(self, auth_client):
        res = auth_client.post(LIST_URL, co_payload(document_number='ABC123'), content_type='application/json')
        assert res.status_code == 422

    def test_mx_amount_exceeds_5x_income_returns_422(self, auth_client):
        res = auth_client.post(
            LIST_URL,
            payload(amount_requested='100000.00', monthly_income='10000.00'),
            content_type='application/json',
        )
        assert res.status_code == 422

    def test_co_debt_exceeds_40pct_income_returns_422(self, auth_client):
        """total_debt mock = 2000. income=1000 → 1000*0.4=400 < 2000 → falla."""
        res = auth_client.post(
            LIST_URL,
            co_payload(monthly_income='1000.00'),
            content_type='application/json',
        )
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# Listar solicitudes
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestList:
    def test_list_returns_only_own_applications(self, auth_client, other_auth_client):
        auth_client.post(LIST_URL, payload(), content_type='application/json')
        auth_client.post(LIST_URL, co_payload(), content_type='application/json')
        other_auth_client.post(LIST_URL, payload(), content_type='application/json')

        res = auth_client.get(LIST_URL)
        assert res.status_code == 200
        assert res.json()['count'] == 2

    def test_list_filter_by_country(self, auth_client):
        auth_client.post(LIST_URL, payload(), content_type='application/json')
        auth_client.post(LIST_URL, co_payload(), content_type='application/json')

        res = auth_client.get(LIST_URL + '?country=MX')
        assert res.status_code == 200
        results = res.json()['results']
        assert len(results) == 1
        assert results[0]['country'] == 'MX'

    def test_list_filter_country_case_insensitive(self, auth_client):
        auth_client.post(LIST_URL, co_payload(), content_type='application/json')
        res = auth_client.get(LIST_URL + '?country=co')
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


# ---------------------------------------------------------------------------
# Historial de estado
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStatusHistory:
    def test_status_update_creates_history_entry(self, auth_client, user):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'under_review'}, content_type='application/json')

        history = ApplicationStatusHistory.objects.filter(application_id=pk)
        assert history.count() == 1
        entry = history.first()
        assert entry.from_status == 'pending'
        assert entry.to_status == 'under_review'
        assert entry.changed_by == user.email

    def test_multiple_transitions_create_multiple_entries(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'under_review'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')

        assert ApplicationStatusHistory.objects.filter(application_id=pk).count() == 2
