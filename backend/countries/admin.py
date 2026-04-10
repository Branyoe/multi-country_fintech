from django.contrib import admin
from .models import Country, CountryValidation


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display  = ('code', 'label', 'document_type', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('code', 'label')


@admin.register(CountryValidation)
class CountryValidationAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'rule_name', 'passed', 'detail', 'evaluated_at')
    list_filter = ('passed', 'rule_name')
    readonly_fields = ('id', 'evaluated_at')
