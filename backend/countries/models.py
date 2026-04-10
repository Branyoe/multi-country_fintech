import uuid
from django.db import models


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
