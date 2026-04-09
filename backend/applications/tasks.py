from celery import shared_task


@shared_task(bind=True, max_retries=3)
def process_application(self, application_id: str):
    """
    Procesa una solicitud de crédito de forma asíncrona.
    Actualmente mueve el estado pending → under_review.
    En el futuro orquestará validaciones adicionales, notificaciones y webhooks.
    """
    from .models import CreditApplication

    try:
        app = CreditApplication.objects.get(id=application_id)
        if app.status == CreditApplication.Status.PENDING:
            app.status = CreditApplication.Status.UNDER_REVIEW
            app.save(update_fields=['status', 'updated_at'])
    except CreditApplication.DoesNotExist:
        pass
