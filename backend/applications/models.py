import uuid
from django.conf import settings
from django.db import models


class CreditApplication(models.Model):

    class Country(models.TextChoices):
        ES = 'ES', 'España'
        PT = 'PT', 'Portugal'
        IT = 'IT', 'Italia'
        MX = 'MX', 'México'
        CO = 'CO', 'Colombia'
        BR = 'BR', 'Brasil'

    class DocumentType(models.TextChoices):
        DNI             = 'DNI',             'DNI (España)'
        NIF             = 'NIF',             'NIF (Portugal)'
        CODICE_FISCALE  = 'CODICE_FISCALE',  'Codice Fiscale (Italia)'
        CURP            = 'CURP',            'CURP (México)'
        CC              = 'CC',              'Cédula de Ciudadanía (Colombia)'
        CPF             = 'CPF',             'CPF (Brasil)'

    class Status(models.TextChoices):
        PENDING      = 'pending',      'Pending'
        UNDER_REVIEW = 'under_review', 'Under Review'
        APPROVED     = 'approved',     'Approved'
        REJECTED     = 'rejected',     'Rejected'

    # Documento requerido por país
    COUNTRY_DOCUMENT_MAP = {
        Country.ES: DocumentType.DNI,
        Country.PT: DocumentType.NIF,
        Country.IT: DocumentType.CODICE_FISCALE,
        Country.MX: DocumentType.CURP,
        Country.CO: DocumentType.CC,
        Country.BR: DocumentType.CPF,
    }

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='applications')
    country          = models.CharField(max_length=2, choices=Country.choices)
    full_name        = models.CharField(max_length=255)
    document_type    = models.CharField(max_length=20, choices=DocumentType.choices)
    document_number  = models.CharField(max_length=50)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_income   = models.DecimalField(max_digits=12, decimal_places=2)
    status           = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at     = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'credit_applications'
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.country} | {self.full_name} | {self.status}'


class BankProviderData(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application    = models.OneToOneField(CreditApplication, on_delete=models.PROTECT, related_name='bank_data')
    provider_name  = models.CharField(max_length=100)
    total_debt     = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    credit_score   = models.IntegerField(null=True, blank=True)
    account_status = models.CharField(max_length=50)
    raw_response   = models.JSONField(default=dict)
    fetched_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bank_provider_data'

    def __str__(self):
        return f'{self.provider_name} | {self.application_id}'


class CountryValidation(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application  = models.ForeignKey(CreditApplication, on_delete=models.PROTECT, related_name='validations')
    rule_name    = models.CharField(max_length=100)
    passed       = models.BooleanField()
    detail       = models.CharField(max_length=255, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'country_validations'

    def __str__(self):
        return f'{self.rule_name} | {"OK" if self.passed else "FAIL"}'


class ApplicationStatusHistory(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(CreditApplication, on_delete=models.PROTECT, related_name='status_history')
    from_status = models.CharField(max_length=20)
    to_status   = models.CharField(max_length=20)
    changed_by  = models.CharField(max_length=255)
    changed_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'application_status_history'
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.from_status} → {self.to_status} by {self.changed_by}'
