from django.contrib import admin
from .models import Country, CountryStatus, CountryValidation, StatusTransition


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display  = ('code', 'label', 'document_type', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('code', 'label')


class StatusTransitionInline(admin.TabularInline):
    model = StatusTransition
    fk_name = 'from_status'
    extra = 0
    fields = ('to_status', 'triggers_task')


@admin.register(CountryStatus)
class CountryStatusAdmin(admin.ModelAdmin):
    list_display  = ('country', 'code', 'label', 'is_initial', 'is_terminal', 'order')
    list_filter   = ('country', 'is_initial', 'is_terminal')
    ordering      = ('country', 'order')
    inlines       = [StatusTransitionInline]


@admin.register(StatusTransition)
class StatusTransitionAdmin(admin.ModelAdmin):
    list_display  = ('from_status', 'to_status', 'triggers_task')
    list_filter   = ('from_status__country',)


@admin.register(CountryValidation)
class CountryValidationAdmin(admin.ModelAdmin):
    list_display = ('id', 'application', 'rule_name', 'passed', 'detail', 'evaluated_at')
    list_filter = ('passed', 'rule_name')
    readonly_fields = ('id', 'evaluated_at')
