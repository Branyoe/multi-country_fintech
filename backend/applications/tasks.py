from celery import shared_task


@shared_task(bind=True, max_retries=3)
def process_application_mx(self, application_id: str):
    """
    Task asíncrono para México.
    Consulta información bancaria (CNBV), valida reglas financieras y
    transiciona el status: pending → under_review (OK) o pending → rejected (falla).
    """
    from .models import CreditApplication, BankProviderData
    from countries.models import CountryValidation
    from countries.validators.registry import get_validator
    from .services import CreditApplicationService

    try:
        app = CreditApplication.objects.select_related('country_ref', 'status').get(id=application_id)
    except CreditApplication.DoesNotExist:
        return

    if app.status_code != 'pending':
        return

    validator = get_validator(app.country_ref.code)

    try:
        bank_data = validator.fetch_bank_data(app.document_number)
    except Exception as exc:
        # No hacer retry silencioso — loguear y dejar en pending
        raise self.retry(exc=exc, countdown=60)

    # Persistir datos bancarios
    BankProviderData.objects.get_or_create(
        application=app,
        defaults={
            'provider_name':  bank_data.provider_name,
            'account_status': bank_data.account_status,
            'total_debt':     bank_data.total_debt,
            'credit_score':   bank_data.credit_score,
            'raw_response':   bank_data.raw_response,
        },
    )

    # Validar reglas financieras
    amount = float(app.amount_requested)
    income = float(app.monthly_income)
    valid, error_msg, error_field = validator.validate_financial_rules(amount, income, bank_data)

    # Registrar validaciones por regla
    for rule in validator.get_validation_rules():
        CountryValidation.objects.get_or_create(
            application=app,
            rule_name=rule,
            defaults={'passed': valid, 'detail': error_msg if not valid else ''},
        )

    # Transicionar status
    new_status_code = 'under_review' if valid else 'rejected'
    CreditApplicationService.update_status(
        application_id=str(app.id),
        new_status_code=new_status_code,
        changed_by='system:process_application_mx',
    )


@shared_task(bind=True, max_retries=3)
def consulta_buro_co(self, application_id: str):
    """
    Task asíncrono para Colombia.
    Consulta Datacrédito (Buró de crédito), valida reglas financieras y
    transiciona: pending → verificacion_buro (OK) o pending → rejected (falla).
    """
    from .models import CreditApplication, BankProviderData
    from countries.models import CountryValidation
    from countries.validators.registry import get_validator
    from .services import CreditApplicationService

    try:
        app = CreditApplication.objects.select_related('country_ref', 'status').get(id=application_id)
    except CreditApplication.DoesNotExist:
        return

    if app.status_code != 'pending':
        return

    validator = get_validator(app.country_ref.code)

    try:
        bank_data = validator.fetch_bank_data(app.document_number)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

    # Persistir datos bancarios
    BankProviderData.objects.get_or_create(
        application=app,
        defaults={
            'provider_name':  bank_data.provider_name,
            'account_status': bank_data.account_status,
            'total_debt':     bank_data.total_debt,
            'credit_score':   bank_data.credit_score,
            'raw_response':   bank_data.raw_response,
        },
    )

    # Validar reglas financieras
    amount = float(app.amount_requested)
    income = float(app.monthly_income)
    valid, error_msg, error_field = validator.validate_financial_rules(amount, income, bank_data)

    # Registrar validaciones por regla
    for rule in validator.get_validation_rules():
        CountryValidation.objects.get_or_create(
            application=app,
            rule_name=rule,
            defaults={'passed': valid, 'detail': error_msg if not valid else ''},
        )

    # Transicionar status
    new_status_code = 'verificacion_buro' if valid else 'rejected'
    CreditApplicationService.update_status(
        application_id=str(app.id),
        new_status_code=new_status_code,
        changed_by='system:consulta_buro_co',
    )


# Alias para compatibilidad — apunta al task MX
process_application = process_application_mx
