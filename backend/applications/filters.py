import django_filters

from .models import CreditApplication


class CreditApplicationFilter(django_filters.FilterSet):
    country = django_filters.CharFilter(method='filter_country')
    status = django_filters.CharFilter(method='filter_status')

    class Meta:
        model = CreditApplication
        fields = ['country', 'status']

    def _normalized_values(self, value, key: str) -> list[str]:
        values: list[str] = []

        if isinstance(value, list):
            values.extend(str(v).strip() for v in value if str(v).strip())
        elif isinstance(value, str) and value.strip():
            values.extend(part.strip() for part in value.split(',') if part.strip())

        values.extend(
            str(v).strip()
            for v in self.request.query_params.getlist(key)
            if str(v).strip()
        )
        values.extend(
            str(v).strip()
            for v in self.request.query_params.getlist(f'{key}[]')
            if str(v).strip()
        )

        unique: list[str] = []
        for item in values:
            if item not in unique:
                unique.append(item)
        return unique

    def filter_country(self, queryset, name, value):
        countries = [v.upper() for v in self._normalized_values(value, name)]
        if not countries:
            return queryset
        return queryset.filter(country_ref__code__in=countries)

    def filter_status(self, queryset, name, value):
        statuses = self._normalized_values(value, name)
        if not statuses:
            return queryset
        return queryset.filter(status__in=statuses)
