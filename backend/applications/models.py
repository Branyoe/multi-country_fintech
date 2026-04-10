import uuid
from django.conf import settings
from django.db import models


class CreditApplication(models.Model):

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='applications')
    country_ref      = models.ForeignKey('countries.Country', on_delete=models.PROTECT, related_name='applications', null=True, blank=True)
    full_name        = models.CharField(max_length=255)
    document_type    = models.CharField(max_length=20)
    document_number  = models.CharField(max_length=50)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_income   = models.DecimalField(max_digits=12, decimal_places=2)
    status           = models.ForeignKey('countries.CountryStatus', on_delete=models.PROTECT, related_name='applications', null=True, blank=True)
    requested_at     = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'credit_applications'
        ordering = ['-requested_at']

    @property
    def country(self) -> str:
        return self.country_ref.code if self.country_ref_id else ''

    @property
    def status_code(self) -> str:
        return self.status.code if self.status_id else ''

    def __str__(self):
        return f'{self.country} | {self.full_name} | {self.status_code}'


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


