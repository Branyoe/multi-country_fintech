from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from countries.models import CountryValidation
from countries.validators.registry import get_validator
from .models import (
    ApplicationStatusHistory,
    BankProviderData,
    CreditApplication,
)


class BankProviderError(Exception):
    pass


class CreditApplicationService:

    @staticmethod
    def create(data: dict, user) -> CreditApplication:
        country = data['country']

        # 1. Resolver validator del país
        try:
            validator = get_validator(country)
        except ValueError as exc:
            raise exc  # re-raise — view lo captura como 400

        # 2. Validar formato del documento
        document = data['document_number']
        valid, error_msg = validator.validate_document(document)
        if not valid:
            raise ValidationError({'document_number': error_msg})

        # 3. Obtener datos del proveedor bancario (mock)
        try:
            bank_data = validator.fetch_bank_data(document)
        except Exception as exc:
            raise BankProviderError('No se pudo consultar el proveedor bancario') from exc

        # 4. Validar reglas financieras del país
        amount = float(data['amount_requested'])
        income = float(data['monthly_income'])
        valid, error_msg, error_field = validator.validate_financial_rules(amount, income, bank_data)
        if not valid:
            raise ValidationError({error_field: error_msg})

        # 5. Persistir solicitud
        application = CreditApplication.objects.create(
            user=user,
            country=country,
            full_name=data['full_name'],
            document_type=validator.get_document_type(),
            document_number=document,
            amount_requested=data['amount_requested'],
            monthly_income=data['monthly_income'],
            status=validator.get_initial_status(),
        )

        # 6. Persistir datos bancarios
        BankProviderData.objects.create(
            application=application,
            provider_name=bank_data.provider_name,
            account_status=bank_data.account_status,
            total_debt=bank_data.total_debt,
            credit_score=bank_data.credit_score,
            raw_response=bank_data.raw_response,
        )

        # 7. Registrar validaciones por regla
        for rule in validator.get_validation_rules():
            CountryValidation.objects.create(
                application=application,
                rule_name=rule,
                passed=True,
                detail='',
            )

        # 8. Disparar task asíncrono
        from .tasks import process_application
        process_application.delay(str(application.id))

        return application

    @staticmethod
    def update_status(
        application_id: str, new_status: str, changed_by: str
    ) -> CreditApplication:
        application = get_object_or_404(CreditApplication, id=application_id)
        from_status = application.status

        application.status = new_status
        application.save(update_fields=['status', 'updated_at'])

        ApplicationStatusHistory.objects.create(
            application=application,
            from_status=from_status,
            to_status=new_status,
            changed_by=changed_by,
        )

        return application
