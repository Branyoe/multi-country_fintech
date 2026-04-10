import pytest
import json
from unittest.mock import patch
from urllib.error import URLError
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from celery.exceptions import Retry

from countries.models import Country, CountryValidation
from applications.models import ApplicationStatusHistory, BankProviderData, CreditApplication

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

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(email='admin@test.com', password='pass1234', role='admin')

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

@pytest.fixture
def admin_auth_client(admin_user):
    return _make_auth_client('admin@test.com', 'pass1234')

@pytest.fixture(autouse=True)
def mock_workflow_tasks():
    """Avoid real async dispatch and assert workflow side effects explicitly."""
    with (
        patch('applications.tasks.fetching_bank_data_task.delay') as fetching_delay,
        patch('applications.tasks.validate_country_rules_task.delay') as validate_delay,
        patch('applications.tasks.notify_final_decision_task.delay') as notify_delay,
    ):
        yield {
            'fetching': fetching_delay,
            'validate': validate_delay,
            'notify': notify_delay,
        }


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
    def test_create_mx_success(self, auth_client, mock_workflow_tasks):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.status_code == 201
        data = res.json()
        assert data['country'] == 'MX'
        assert data['status'] == 'fetching_bank_data'
        assert data['document_type'] == 'CURP'
        assert 'id' in data
        mock_workflow_tasks['fetching'].assert_called_once_with(data['id'])

    def test_create_co_success(self, auth_client, mock_workflow_tasks):
        res = auth_client.post(LIST_URL, co_payload(), content_type='application/json')
        assert res.status_code == 201
        data = res.json()
        assert data['country'] == 'CO'
        assert data['status'] == 'fetching_bank_data'
        assert data['document_type'] == 'CC'
        mock_workflow_tasks['fetching'].assert_called_once_with(data['id'])

    def test_create_sets_status_created(self, auth_client):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.json()['status'] == 'fetching_bank_data'

    def test_create_document_type_set_by_service(self, auth_client):
        """El cliente no envía document_type — lo fija el service."""
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.status_code == 201
        assert res.json()['document_type'] == 'CURP'

    def test_create_document_type_comes_from_country_catalog(self, auth_client):
        country = Country.objects.get(code='MX')
        country.document_type = 'CURP_ALT'
        country.save(update_fields=['document_type'])

        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        assert res.status_code == 201
        assert res.json()['document_type'] == 'CURP_ALT'

    def test_create_missing_required_field(self, auth_client):
        data = payload()
        del data['full_name']
        res = auth_client.post(LIST_URL, data, content_type='application/json')
        assert res.status_code == 400

    def test_create_negative_amount(self, auth_client):
        res = auth_client.post(LIST_URL, payload(amount_requested='-100'), content_type='application/json')
        assert res.status_code == 400

    def test_create_invalid_country_choice(self, auth_client):
        """País fuera del catálogo activo → 400."""
        res = auth_client.post(LIST_URL, payload(country='XX'), content_type='application/json')
        assert res.status_code == 400

    def test_unsupported_country_returns_400(self, auth_client):
        """Países no activos/no configurados en catálogo deben fallar."""
        for country in ['ES', 'PT', 'IT', 'BR']:
            res = auth_client.post(LIST_URL, payload(country=country), content_type='application/json')
            assert res.status_code == 400, f'{country} debería retornar 400'

    def test_inactive_country_returns_400(self, auth_client):
        co = Country.objects.get(code='CO')
        co.is_active = False
        co.save(update_fields=['is_active'])

        res = auth_client.post(LIST_URL, co_payload(), content_type='application/json')
        assert res.status_code == 400

    def test_create_creates_initial_history_entry(self, auth_client):
        """La creación registra historia inicial y bootstrap del pipeline."""
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        pk = res.json()['id']
        history = ApplicationStatusHistory.objects.filter(application_id=pk).order_by('changed_at')
        assert history.count() == 2
        entry = history.first()
        assert entry.from_status == ''
        assert entry.to_status == 'created'

        bootstrap = history.last()
        assert bootstrap.from_status == 'created'
        assert bootstrap.to_status == 'fetching_bank_data'

    def test_create_mx_country_ref_set(self, auth_client):
        res = auth_client.post(LIST_URL, payload(), content_type='application/json')
        app = CreditApplication.objects.get(id=res.json()['id'])
        assert app.country_ref is not None
        assert app.country_ref.code == 'MX'

# ---------------------------------------------------------------------------
# Validación de documentos (síncrona — sigue retornando 422)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestValidation:
    def test_invalid_curp_returns_422(self, auth_client):
        res = auth_client.post(LIST_URL, payload(document_number='INVALIDO'), content_type='application/json')
        assert res.status_code == 422

    def test_invalid_cc_returns_422(self, auth_client):
        res = auth_client.post(LIST_URL, co_payload(document_number='ABC123'), content_type='application/json')
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# Tasks — validación financiera asíncrona
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTasks:
    def _create_app(self, auth_client, data=None):
        """Crea una solicitud y retorna la instancia del modelo."""
        res = auth_client.post(LIST_URL, data or payload(), content_type='application/json')
        assert res.status_code == 201
        return CreditApplication.objects.select_related('country_ref', 'status').get(
            id=res.json()['id']
        )

    def test_mx_tasks_transitions_to_approved_on_success(self, auth_client):
        app = self._create_app(auth_client)
        from applications.tasks import fetching_bank_data_task, validate_country_rules_task
        fetching_bank_data_task(str(app.id))
        validate_country_rules_task(str(app.id))

        app.refresh_from_db()
        assert app.status_code == 'approved'
        assert BankProviderData.objects.filter(application=app).exists()
        rules = list(CountryValidation.objects.filter(application=app).values_list('rule_name', flat=True))
        assert 'curp_format' in rules
        assert 'monto_5x_ingreso' in rules

    def test_mx_task_transitions_to_rejected_when_amount_exceeds_5x_income(self, auth_client):
        """amount > 5x income → task rechaza la solicitud."""
        app = self._create_app(auth_client, payload(amount_requested='100000.00', monthly_income='10000.00'))
        from applications.tasks import fetching_bank_data_task, validate_country_rules_task
        fetching_bank_data_task(str(app.id))
        validate_country_rules_task(str(app.id))

        app.refresh_from_db()
        assert app.status_code == 'rejected'

    def test_co_tasks_transitions_to_approved_on_success(self, auth_client):
        app = self._create_app(auth_client, co_payload())
        from applications.tasks import fetching_bank_data_task, validate_country_rules_task
        fetching_bank_data_task(str(app.id))
        validate_country_rules_task(str(app.id))

        app.refresh_from_db()
        assert app.status_code == 'approved'
        assert BankProviderData.objects.filter(application=app).exists()

    def test_co_task_transitions_to_rejected_when_debt_exceeds_40pct(self, auth_client):
        """total_debt mock = 2000. income=1000 → 1000*0.4=400 < 2000 → rechazada."""
        app = self._create_app(auth_client, co_payload(monthly_income='1000.00'))
        from applications.tasks import fetching_bank_data_task, validate_country_rules_task
        fetching_bank_data_task(str(app.id))
        validate_country_rules_task(str(app.id))

        app.refresh_from_db()
        assert app.status_code == 'rejected'

    def test_mx_task_moves_to_technical_error_when_retries_exhausted(self, auth_client):
        app = self._create_app(auth_client)

        from applications.tasks import fetching_bank_data_task

        with patch('countries.validators.mx.MXCountryValidator.fetch_bank_data', side_effect=Exception('provider-down')):
            with patch.object(fetching_bank_data_task, 'max_retries', new=0):
                fetching_bank_data_task(str(app.id))

        app.refresh_from_db()
        assert app.status_code == 'technical_error'

    def test_task_noop_if_status_mismatch(self, auth_client):
        """Idempotency guard: task exits when current state does not match."""
        app = self._create_app(auth_client)
        from applications.services import CreditApplicationService
        CreditApplicationService.update_status(str(app.id), 'validate_country_rules', 'test')

        from applications.tasks import fetching_bank_data_task
        fetching_bank_data_task(str(app.id))

        app.refresh_from_db()
        assert app.status_code == 'validate_country_rules'

    def test_notify_final_decision_sends_webhook(self, auth_client, settings):
        app = self._create_app(auth_client)
        settings.WEBHOOK_URL = 'https://example.com/webhook'
        settings.WEBHOOK_TIMEOUT_SECONDS = 3

        from applications.tasks import fetching_bank_data_task, validate_country_rules_task, notify_final_decision_task

        with patch('applications.tasks.delay', return_value=None):
            fetching_bank_data_task(str(app.id))
            validate_country_rules_task(str(app.id))

        app.refresh_from_db()
        assert app.status_code == 'approved'

        with patch('applications.tasks.delay', return_value=None):
            with patch('applications.tasks.urlopen') as mock_urlopen:
                notify_final_decision_task(str(app.id))

        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args.args[0]
        timeout = mock_urlopen.call_args.kwargs['timeout']

        assert req.full_url == 'https://example.com/webhook'
        assert timeout == 3

        payload = json.loads(req.data.decode('utf-8'))
        assert payload['event'] == 'decision.finalized'
        assert payload['application_id'] == str(app.id)
        assert payload['status'] == 'approved'
        assert payload['idempotency_key'] == f'final-decision:{app.id}:approved'

    def test_notify_final_decision_skips_without_webhook_url(self, auth_client, settings):
        app = self._create_app(auth_client)
        settings.WEBHOOK_URL = ''

        from applications.tasks import fetching_bank_data_task, validate_country_rules_task, notify_final_decision_task

        with patch('applications.tasks.delay', return_value=None):
            fetching_bank_data_task(str(app.id))
            validate_country_rules_task(str(app.id))

        with patch('applications.tasks.delay', return_value=None):
            with patch('applications.tasks.urlopen') as mock_urlopen:
                notify_final_decision_task(str(app.id))

        mock_urlopen.assert_not_called()

    def test_notify_final_decision_noop_non_terminal_status(self, auth_client, settings):
        app = self._create_app(auth_client)
        settings.WEBHOOK_URL = 'https://example.com/webhook'

        from applications.tasks import notify_final_decision_task

        with patch('applications.tasks.delay', return_value=None):
            with patch('applications.tasks.urlopen') as mock_urlopen:
                notify_final_decision_task(str(app.id))

        mock_urlopen.assert_not_called()

    def test_notify_final_decision_retries_on_webhook_error(self, auth_client, settings):
        app = self._create_app(auth_client)
        settings.WEBHOOK_URL = 'https://example.com/webhook'
        settings.WEBHOOK_RETRY_COUNTDOWN_SECONDS = 42

        from applications.tasks import fetching_bank_data_task, validate_country_rules_task, notify_final_decision_task

        with patch('applications.tasks.delay', return_value=None):
            fetching_bank_data_task(str(app.id))
            validate_country_rules_task(str(app.id))

        with patch('applications.tasks.delay', return_value=None):
            with patch('applications.tasks.urlopen', side_effect=URLError('connection error')):
                with patch.object(notify_final_decision_task, 'retry', side_effect=Retry()) as mock_retry:
                    with pytest.raises(Retry):
                        notify_final_decision_task(str(app.id))

        mock_retry.assert_called_once()
        assert mock_retry.call_args.kwargs['countdown'] == 42

    def test_notify_final_decision_returns_when_retries_exhausted(self, auth_client, settings):
        app = self._create_app(auth_client)
        settings.WEBHOOK_URL = 'https://example.com/webhook'

        from applications.tasks import fetching_bank_data_task, validate_country_rules_task, notify_final_decision_task

        with patch('applications.tasks.delay', return_value=None):
            fetching_bank_data_task(str(app.id))
            validate_country_rules_task(str(app.id))

        with patch('applications.tasks.delay', return_value=None):
            with patch('applications.tasks.urlopen', side_effect=URLError('connection error')) as mock_urlopen:
                with patch.object(notify_final_decision_task, 'max_retries', new=0):
                    notify_final_decision_task(str(app.id))

        mock_urlopen.assert_called_once()


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

    def test_admin_can_list_all_applications(self, auth_client, other_auth_client, admin_auth_client):
        auth_client.post(LIST_URL, payload(), content_type='application/json')
        other_auth_client.post(LIST_URL, co_payload(), content_type='application/json')

        res = admin_auth_client.get(LIST_URL)
        assert res.status_code == 200
        assert res.json()['count'] == 2

    def test_admin_can_retrieve_any_application(self, auth_client, admin_auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']

        res = admin_auth_client.get(DETAIL_URL(pk))
        assert res.status_code == 200
        assert res.json()['id'] == pk

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

    def test_list_filter_status_multiple(self, auth_client):
        created_id = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        fetching_id = auth_client.post(LIST_URL, payload(document_number='PERJ800101HDFRZN08'), content_type='application/json').json()['id']

        # Transicionar a fetching_bank_data
        auth_client.patch(DETAIL_URL(fetching_id), {'status': 'fetching_bank_data'}, content_type='application/json')

        res = auth_client.get(LIST_URL + '?status=created&status=fetching_bank_data')
        assert res.status_code == 200
        ids = {row['id'] for row in res.json()['results']}
        assert created_id in ids
        assert fetching_id in ids

    def test_list_filter_country_and_status(self, auth_client):
        mx_id = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        co_id = auth_client.post(LIST_URL, co_payload(), content_type='application/json').json()['id']

        # CO: fetching_bank_data → validate_country_rules → approved
        auth_client.patch(DETAIL_URL(co_id), {'status': 'validate_country_rules'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(co_id), {'status': 'approved'}, content_type='application/json')

        res = auth_client.get(LIST_URL + '?country=CO&status=approved')
        assert res.status_code == 200
        rows = res.json()['results']
        assert len(rows) == 1
        assert rows[0]['id'] == co_id
        assert rows[0]['country'] == 'CO'
        assert rows[0]['status'] == 'approved'

        res_mx = auth_client.get(LIST_URL + '?country=MX&status=approved')
        assert res_mx.status_code == 200
        assert not any(row['id'] == mx_id for row in res_mx.json()['results'])

    def test_list_empty_for_new_user(self, auth_client):
        res = auth_client.get(LIST_URL)
        assert res.status_code == 200
        assert res.json()['count'] == 0

    def test_list_ordering_by_full_name(self, auth_client):
        auth_client.post(
            LIST_URL,
            payload(full_name='Zoe Alpha', document_number='PERJ800101HDFRZN08'),
            content_type='application/json',
        )
        auth_client.post(
            LIST_URL,
            payload(full_name='Ana Beta', document_number='PERJ800101HDFRZN07'),
            content_type='application/json',
        )

        asc = auth_client.get(LIST_URL + '?ordering=full_name')
        assert asc.status_code == 200
        asc_names = [row['full_name'] for row in asc.json()['results']]
        assert asc_names[:2] == ['Ana Beta', 'Zoe Alpha']

        desc = auth_client.get(LIST_URL + '?ordering=-full_name')
        assert desc.status_code == 200
        desc_names = [row['full_name'] for row in desc.json()['results']]
        assert desc_names[:2] == ['Zoe Alpha', 'Ana Beta']

    def test_list_ordering_by_country_code(self, auth_client):
        auth_client.post(
            LIST_URL,
            payload(country='MX', document_number='PERJ800101HDFRZN01'),
            content_type='application/json',
        )
        auth_client.post(
            LIST_URL,
            co_payload(document_number='1234567891'),
            content_type='application/json',
        )

        asc = auth_client.get(LIST_URL + '?ordering=country_ref__code')
        assert asc.status_code == 200
        asc_countries = [row['country'] for row in asc.json()['results']]
        assert asc_countries[:2] == ['CO', 'MX']

        desc = auth_client.get(LIST_URL + '?ordering=-country_ref__code')
        assert desc.status_code == 200
        desc_countries = [row['country'] for row in desc.json()['results']]
        assert desc_countries[:2] == ['MX', 'CO']

    def test_list_ordering_by_document_type(self, auth_client):
        auth_client.post(
            LIST_URL,
            payload(country='MX', document_number='PERJ800101HDFRZN06'),
            content_type='application/json',
        )
        auth_client.post(
            LIST_URL,
            co_payload(document_number='2233445566'),
            content_type='application/json',
        )

        asc = auth_client.get(LIST_URL + '?ordering=document_type')
        assert asc.status_code == 200
        asc_types = [row['document_type'] for row in asc.json()['results']]
        assert asc_types[:2] == ['CC', 'CURP']

        desc = auth_client.get(LIST_URL + '?ordering=-document_type')
        assert desc.status_code == 200
        desc_types = [row['document_type'] for row in desc.json()['results']]
        assert desc_types[:2] == ['CURP', 'CC']

    def test_list_ordering_by_document_number(self, auth_client):
        mx_res = auth_client.post(
            LIST_URL,
            payload(document_number='PERJ800101HDFRZN98'),
            content_type='application/json',
        )
        assert mx_res.status_code == 201

        co_res = auth_client.post(
            LIST_URL,
            co_payload(document_number='1111111111'),
            content_type='application/json',
        )
        assert co_res.status_code == 201

        asc = auth_client.get(LIST_URL + '?ordering=document_number')
        assert asc.status_code == 200
        asc_numbers = [row['document_number'] for row in asc.json()['results']]
        assert asc_numbers[:2] == ['1111111111', 'PERJ800101HDFRZN98']

        desc = auth_client.get(LIST_URL + '?ordering=-document_number')
        assert desc.status_code == 200
        desc_numbers = [row['document_number'] for row in desc.json()['results']]
        assert desc_numbers[:2] == ['PERJ800101HDFRZN98', '1111111111']


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

    def test_retrieve_includes_status_history(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')

        res = auth_client.get(DETAIL_URL(pk))
        assert res.status_code == 200
        data = res.json()
        assert 'status_history' in data
        assert isinstance(data['status_history'], list)
        assert len(data['status_history']) >= 2

        first = data['status_history'][0]
        assert 'from_status' in first
        assert 'to_status' in first
        assert 'changed_by' in first
        assert 'changed_at' in first
        assert 'metadata' in first


# ---------------------------------------------------------------------------
# Actualizar estado
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStatusUpdate:
    def test_update_created_to_fetching_bank_data(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')
        assert res.status_code == 200
        assert res.json()['status'] == 'validate_country_rules'

    def test_update_validate_country_rules_to_approved(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'fetching_bank_data'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        assert res.status_code == 200
        assert res.json()['status'] == 'approved'

    def test_update_validate_country_rules_to_rejected(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'fetching_bank_data'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'rejected'}, content_type='application/json')
        assert res.status_code == 200
        assert res.json()['status'] == 'rejected'

    def test_invalid_transition_created_to_approved_returns_400(self, auth_client):
        """MX: no hay transición directa created → approved."""
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        assert res.status_code == 400

    def test_invalid_transition_created_to_rejected(self, auth_client):
        """created → rejected directo no está permitido."""
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'rejected'}, content_type='application/json')
        assert res.status_code == 400

    def test_invalid_transition_approved_to_created(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'fetching_bank_data'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'created'}, content_type='application/json')
        assert res.status_code == 400

    def test_invalid_transition_rejected_to_approved(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'fetching_bank_data'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')
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

    def test_co_custom_flow_pending_fetching_validate(self, auth_client):
        """CO now mirrors MX with pending -> fetching_bank_data -> validate_country_rules."""
        pk = auth_client.post(LIST_URL, co_payload(), content_type='application/json').json()['id']

        res = auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')
        assert res.status_code == 200
        assert res.json()['status'] == 'validate_country_rules'

        res = auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        assert res.status_code == 200
        assert res.json()['status'] == 'approved'

    def test_co_cannot_skip_fetching_bank_data(self, auth_client):
        """CO: pending -> validate_country_rules direct transition is not allowed."""
        pk = auth_client.post(LIST_URL, co_payload(), content_type='application/json').json()['id']
        res = auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')
        assert res.status_code == 400

    def test_transition_auto_dispatches_task_via_workflow(self, auth_client, mock_workflow_tasks):
        """Every state transition dispatches side effects from workflow.on_enter."""
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        mock_workflow_tasks['validate'].reset_mock()

        auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')

        mock_workflow_tasks['validate'].assert_called_once_with(pk)


# ---------------------------------------------------------------------------
# Historial de estado
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStatusHistory:
    def test_create_registers_initial_history(self, auth_client):
        """create() registers initial status plus pipeline bootstrap transition."""
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        history = ApplicationStatusHistory.objects.filter(application_id=pk).order_by('changed_at')
        assert history.count() == 2
        entry = history.first()
        assert entry.from_status == ''
        assert entry.to_status == 'created'
        assert entry.metadata.get('event') == 'created'

        bootstrap = history.last()
        assert bootstrap.from_status == 'created'
        assert bootstrap.to_status == 'fetching_bank_data'
        assert bootstrap.metadata.get('event') == 'pipeline_started'

    def test_status_update_creates_history_entry(self, auth_client, user):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')

        history = ApplicationStatusHistory.objects.filter(application_id=pk).order_by('changed_at')
        assert history.count() == 3
        transition = history.last()
        assert transition.from_status == 'fetching_bank_data'
        assert transition.to_status == 'validate_country_rules'
        assert transition.changed_by == user.email

    def test_multiple_transitions_create_multiple_entries(self, auth_client):
        pk = auth_client.post(LIST_URL, payload(), content_type='application/json').json()['id']
        auth_client.patch(DETAIL_URL(pk), {'status': 'fetching_bank_data'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(pk), {'status': 'validate_country_rules'}, content_type='application/json')
        auth_client.patch(DETAIL_URL(pk), {'status': 'approved'}, content_type='application/json')

        # initial + 3 transiciones = 4
        assert ApplicationStatusHistory.objects.filter(application_id=pk).count() == 4
