from django.contrib import admin
from countries.models import CountryValidation
from .models import (
    ApplicationStatusHistory,
    BankProviderData,
    CreditApplication,
)


class BankProviderDataInline(admin.StackedInline):
    model = BankProviderData
    extra = 0
    readonly_fields = ('id', 'provider_name', 'account_status', 'total_debt', 'credit_score', 'raw_response', 'fetched_at')
    can_delete = False


class CountryValidationInline(admin.TabularInline):
    model = CountryValidation
    extra = 0
    readonly_fields = ('id', 'rule_name', 'passed', 'detail', 'evaluated_at')
    can_delete = False


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = ('id', 'from_status', 'to_status', 'changed_by', 'changed_at')
    can_delete = False


@admin.register(CreditApplication)
class CreditApplicationAdmin(admin.ModelAdmin):
    list_display    = ('id', 'user', 'country', 'full_name', 'document_type', 'amount_requested', 'status', 'requested_at')
    list_filter     = ('status', 'country_ref', 'document_type')
    search_fields   = ('full_name', 'document_number', 'user__email')
    readonly_fields = ('id', 'requested_at', 'updated_at')
    ordering        = ('-requested_at',)
    inlines         = [BankProviderDataInline, CountryValidationInline, ApplicationStatusHistoryInline]

    fieldsets = (
        ('Solicitante', {
            'fields': ('id', 'user', 'full_name', 'document_type', 'document_number'),
        }),
        ('Solicitud', {
            'fields': ('country_ref', 'amount_requested', 'monthly_income', 'status'),
        }),
        ('Fechas', {
            'fields': ('requested_at', 'updated_at'),
        }),
    )


@admin.register(BankProviderData)
class BankProviderDataAdmin(admin.ModelAdmin):
    list_display  = ('id', 'application', 'provider_name', 'account_status', 'total_debt', 'credit_score', 'fetched_at')
    list_filter   = ('provider_name', 'account_status')
    readonly_fields = ('id', 'fetched_at')


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display  = ('id', 'application', 'from_status', 'to_status', 'changed_by', 'changed_at')
    list_filter   = ('from_status', 'to_status')
    readonly_fields = ('id', 'changed_at')


