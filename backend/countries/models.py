import uuid
from django.db import models
from django.core.exceptions import ValidationError


class Country(models.Model):
    code             = models.CharField(max_length=10, unique=True)
    label            = models.CharField(max_length=100)
    document_type    = models.CharField(max_length=50)
    document_hint    = models.CharField(max_length=200)
    document_example = models.CharField(max_length=100)
    document_regex   = models.CharField(max_length=500)
    is_active        = models.BooleanField(default=True)

    class Meta:
        db_table = 'country'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.label}'


class CountryStatus(models.Model):
    """Un estado posible de solicitud de crédito para un país específico."""
    country     = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='statuses')
    code        = models.CharField(max_length=50)
    label       = models.CharField(max_length=100)
    is_initial  = models.BooleanField(default=False, help_text='Estado inicial al crear la solicitud')
    is_terminal = models.BooleanField(default=False, help_text='No acepta más transiciones')
    order       = models.IntegerField(default=0, help_text='Orden de presentación en UI')

    class Meta:
        db_table = 'country_status'
        unique_together = [('country', 'code')]
        ordering = ['country', 'order']

    def __str__(self):
        return f'{self.country.code} · {self.code}'


class StatusTransition(models.Model):
    """Transición permitida entre dos estados de un país."""
    from_status   = models.ForeignKey(CountryStatus, on_delete=models.CASCADE, related_name='outgoing_transitions')
    to_status     = models.ForeignKey(CountryStatus, on_delete=models.CASCADE, related_name='incoming_transitions')

    class Meta:
        db_table = 'status_transition'
        unique_together = [('from_status', 'to_status')]

    def clean(self):
        if self.from_status_id and self.to_status_id and self.from_status.country_id != self.to_status.country_id:
            raise ValidationError({'to_status': 'La transición debe ocurrir dentro del mismo país.'})

    def __str__(self):
        return f'{self.from_status.code} → {self.to_status.code}'


class CountryValidation(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application  = models.ForeignKey('applications.CreditApplication', on_delete=models.PROTECT, related_name='validations')
    rule_name    = models.CharField(max_length=100)
    passed       = models.BooleanField()
    detail       = models.CharField(max_length=255, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'country_validations'
        verbose_name_plural = 'Country Validations'

    def __str__(self):
        return f'{self.rule_name} | {"OK" if self.passed else "FAIL"}'
