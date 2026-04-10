import logging

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from countries.models import Country, CountryStatus, CountryValidation, StatusTransition
from countries.validators.registry import get_validator
from .workflows.registry import get_workflow
from .models import ApplicationStatusHistory, BankProviderData, CreditApplication


class BankProviderError(Exception):
    pass


logger = logging.getLogger(__name__)


class CreditApplicationService:

    @staticmethod
    def _create_status_history(
        application: CreditApplication,
        from_status: str,
        to_status: str,
        changed_by: str,
        metadata: dict | None = None,
    ) -> None:
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            metadata=metadata or {},
        )

    @staticmethod
    def create(data: dict, user) -> CreditApplication:
        country_code = str(data['country']).strip().upper()
        country_meta = Country.objects.filter(code=country_code, is_active=True).first()
        if country_meta is None:
            raise ValueError(f'País no soportado o inactivo: {country_code}')

        # Resolver validator del país
        try:
            validator = get_validator(country_code)
        except ValueError:
            raise

        # Validar formato del documento (síncrono — solo regex, no llama al banco)
        document = data['document_number']
        valid, error_msg = validator.validate_document(document)
        if not valid:
            raise ValidationError({'document_number': error_msg})

        # Obtener status inicial del país
        initial_status = CountryStatus.objects.filter(
            country=country_meta, is_initial=True
        ).first()
        if initial_status is None:
            raise ValueError(f'País {country_code} sin estado inicial configurado')

        # Persistir solicitud con status inicial
        application = CreditApplication.objects.create(
            user=user,
            country_ref=country_meta,
            full_name=data['full_name'],
            document_type=country_meta.document_type,
            document_number=document,
            amount_requested=data['amount_requested'],
            monthly_income=data['monthly_income'],
            status=initial_status,
        )

        # Registrar historial del status inicial
        CreditApplicationService._create_status_history(
            application=application,
            from_status='',
            to_status=initial_status.code,
            changed_by=user.email,
            metadata={'event': 'created'},
        )

        # Activar flujo state-driven desde el primer estado de procesamiento.
        CreditApplicationService.update_status(
            application_id=str(application.id),
            new_status_code='fetching_bank_data',
            changed_by='system:create',
            metadata={'event': 'pipeline_started'},
        )

        application.refresh_from_db()

        return application

    @staticmethod
    def update_status(
        application_id: str,
        new_status_code: str,
        changed_by: str,
        metadata: dict | None = None,
    ) -> CreditApplication:
        application = get_object_or_404(CreditApplication, id=application_id)
        from_status = application.status

        if from_status and from_status.is_terminal:
            raise ValueError(f"El estado '{from_status.code}' es terminal y no acepta transiciones.")

        new_status = CountryStatus.objects.filter(
            country=application.country_ref,
            code=new_status_code,
        ).first()
        if new_status is None:
            raise ValueError(f"Estado '{new_status_code}' no existe para este país.")

        transition = StatusTransition.objects.filter(
            from_status=from_status,
            to_status=new_status,
        ).first()
        if transition is None:
            from_code = from_status.code if from_status else '—'
            raise ValueError(f"Transición '{from_code}' → '{new_status_code}' no permitida.")

        application.status = new_status
        application.save(update_fields=['status', 'updated_at'])

        CreditApplicationService._create_status_history(
            application=application,
            from_status=from_status.code if from_status else '',
            to_status=new_status.code,
            changed_by=changed_by,
            metadata=metadata,
        )

        logger.info(
            'application-status-transition',
            extra={
                'application_id': str(application.id),
                'country': application.country,
                'from_status': from_status.code if from_status else '',
                'to_status': new_status.code,
                'changed_by': changed_by,
            },
        )

        # Orquestación única del flujo asíncrono por entrada de estado.
        workflow = get_workflow(application.country)
        workflow.on_enter(new_status.code, application)

        return application
