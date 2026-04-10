import logging
import random
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from celery import shared_task
from .utils import delay


logger = logging.getLogger(__name__)


def _build_final_decision_webhook_payload(app) -> dict:
    return {
        'event': 'decision.finalized',
        'application_id': str(app.id),
        'status': app.status_code,
        'country': app.country,
        'user_id': str(app.user_id),
        'amount_requested': str(app.amount_requested),
        'monthly_income': str(app.monthly_income),
        'decided_at': app.updated_at.isoformat(),
        'source_task': 'notify_final_decision_task',
        'idempotency_key': f'final-decision:{app.id}:{app.status_code}',
    }


def _send_webhook(url: str, payload: dict, timeout_seconds: int) -> int:
    import json

    req = Request(
        url=url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'X-Event-Type': payload['event'],
            'X-Idempotency-Key': payload['idempotency_key'],
        },
        method='POST',
    )
    with urlopen(req, timeout=timeout_seconds) as response:
        return int(response.getcode() or 200)


@shared_task(bind=True, max_retries=3, name='fetching_bank_data_task')
def fetching_bank_data_task(self, application_id: str) -> None:
    """Fetch and persist bank data for any country in fetching_bank_data state."""
    from .models import CreditApplication, BankProviderData
    from countries.validators.registry import get_validator
    from .services import CreditApplicationService

    try:
        app = CreditApplication.objects.select_related('country_ref', 'status').get(id=application_id)
    except CreditApplication.DoesNotExist:
        return

    if app.status_code != 'fetching_bank_data':
        return

    delay(random.randint(3, 8))

    validator = get_validator(app.country_ref.code)

    try:
        bank_data = validator.fetch_bank_data(app.document_number)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            CreditApplicationService.update_status(
                application_id=str(app.id),
                new_status_code='technical_error',
                changed_by='system:fetching_bank_data_task',
                metadata={
                    'task': 'fetching_bank_data_task',
                    'event': 'failed',
                    'reason': str(exc),
                },
            )
            return
        raise self.retry(exc=exc, countdown=60)

    # Persist before transitioning so next state always reads stable data.
    BankProviderData.objects.update_or_create(
        application=app,
        defaults={
            'provider_name': bank_data.provider_name,
            'account_status': bank_data.account_status,
            'total_debt': bank_data.total_debt,
            'credit_score': bank_data.credit_score,
            'raw_response': bank_data.raw_response,
        },
    )

    CreditApplicationService.update_status(
        application_id=str(app.id),
        new_status_code='validate_country_rules',
        changed_by='system:fetching_bank_data_task:success',
        metadata={
            'task': 'fetching_bank_data_task',
            'event': 'success',
        },
    )


@shared_task(bind=True, max_retries=3, name='validate_country_rules_task')
def validate_country_rules_task(self, application_id: str) -> None:
    """Validate country rules and transition to approved or rejected."""
    from .models import CreditApplication
    from countries.models import CountryValidation
    from countries.validators.registry import get_validator
    from .services import CreditApplicationService
    from .workflows.registry import get_workflow

    try:
        app = CreditApplication.objects.select_related('country_ref', 'status', 'bank_data').get(id=application_id)
    except CreditApplication.DoesNotExist:
        return

    if app.status_code != 'validate_country_rules':
        return

    delay(random.randint(3, 8))

    if not hasattr(app, 'bank_data'):
        CreditApplicationService.update_status(
            application_id=str(app.id),
            new_status_code='technical_error',
            changed_by='system:validate_country_rules_task',
            metadata={
                'task': 'validate_country_rules_task',
                'event': 'failed',
                'reason': 'missing_bank_data',
            },
        )
        return

    try:
        workflow = get_workflow(app.country)
        validator = get_validator(app.country_ref.code)
        valid = workflow.validate(app, app.bank_data)
        error_msg = '' if valid else 'financial_rules_failed'

        for rule in validator.get_validation_rules():
            CountryValidation.objects.update_or_create(
                application=app,
                rule_name=rule,
                defaults={
                    'passed': valid,
                    'detail': error_msg if not valid else '',
                },
            )

        CreditApplicationService.update_status(
            application_id=str(app.id),
            new_status_code='approved' if valid else 'rejected',
            changed_by='system:validate_country_rules_task:success',
            metadata={
                'task': 'validate_country_rules_task',
                'event': 'success',
                'valid': valid,
            },
        )
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            CreditApplicationService.update_status(
                application_id=str(app.id),
                new_status_code='technical_error',
                changed_by='system:validate_country_rules_task',
                metadata={
                    'task': 'validate_country_rules_task',
                    'event': 'failed',
                    'reason': str(exc),
                },
            )
            return
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3, name='notify_final_decision_task')
def notify_final_decision_task(self, application_id: str) -> None:
    """Emit final business decision notification side effect."""
    from .models import CreditApplication

    try:
        app = CreditApplication.objects.select_related('status', 'country_ref').get(id=application_id)
    except CreditApplication.DoesNotExist:
        return

    if app.status_code not in {'approved', 'rejected'}:
        return

    delay(random.randint(3, 8))

    log_context = {
        'application_id': str(app.id),
        'status': app.status_code,
        'country': app.country,
        'task': 'notify_final_decision_task',
        'retry_count': self.request.retries,
        'max_retries': self.max_retries,
    }

    webhook_url = settings.WEBHOOK_URL.strip()
    if not webhook_url:
        logger.info(
            'final-decision-webhook',
            extra={
                **log_context,
                'outcome': 'skipped',
                'reason': 'webhook_url_not_configured',
            },
        )
        return

    payload = _build_final_decision_webhook_payload(app)
    request_started_at = time.monotonic()
    log_context.update(
        {
            'webhook_url': webhook_url,
            'webhook_event': payload['event'],
            'idempotency_key': payload['idempotency_key'],
            'timeout_seconds': settings.WEBHOOK_TIMEOUT_SECONDS,
        }
    )

    try:
        status_code = _send_webhook(
            url=webhook_url,
            payload=payload,
            timeout_seconds=settings.WEBHOOK_TIMEOUT_SECONDS,
        )
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        elapsed_ms = int((time.monotonic() - request_started_at) * 1000)
        if self.request.retries >= self.max_retries:
            logger.error(
                'final-decision-webhook',
                extra={
                    **log_context,
                    'outcome': 'failed',
                    'reason': 'retries_exhausted',
                    'error_type': type(exc).__name__,
                    'error_message': str(exc),
                    'elapsed_ms': elapsed_ms,
                },
                exc_info=True,
            )
            return

        logger.warning(
            'final-decision-webhook',
            extra={
                **log_context,
                'outcome': 'retrying',
                'error_type': type(exc).__name__,
                'error_message': str(exc),
                'next_retry_in_seconds': settings.WEBHOOK_RETRY_COUNTDOWN_SECONDS,
                'elapsed_ms': elapsed_ms,
            },
        )
        raise self.retry(exc=exc, countdown=settings.WEBHOOK_RETRY_COUNTDOWN_SECONDS)

    elapsed_ms = int((time.monotonic() - request_started_at) * 1000)
    logger.info(
        'final-decision-webhook',
        extra={
            **log_context,
            'outcome': 'sent',
            'http_status': status_code,
            'elapsed_ms': elapsed_ms,
        },
    )
