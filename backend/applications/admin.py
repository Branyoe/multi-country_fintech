from django.contrib import admin
from .models import CreditApplication


@admin.register(CreditApplication)
class CreditApplicationAdmin(admin.ModelAdmin):
    list_display   = ('id', 'user', 'country', 'full_name', 'document_type', 'amount_requested', 'status', 'requested_at')
    list_filter    = ('status', 'country', 'document_type')
    search_fields  = ('full_name', 'document_number', 'user__email')
    readonly_fields = ('id', 'requested_at', 'updated_at')
    ordering       = ('-requested_at',)

    fieldsets = (
        ('Solicitante', {
            'fields': ('id', 'user', 'full_name', 'document_type', 'document_number'),
        }),
        ('Solicitud', {
            'fields': ('country', 'amount_requested', 'monthly_income', 'status'),
        }),
        ('Fechas', {
            'fields': ('requested_at', 'updated_at'),
        }),
    )
