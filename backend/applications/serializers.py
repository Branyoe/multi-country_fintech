from rest_framework import serializers
from django.core.validators import MinValueValidator
from countries.models import Country, CountryStatus, StatusTransition
from .models import ApplicationStatusHistory, CreditApplication


class CreditApplicationSerializer(serializers.ModelSerializer):
    """Serializer de escritura — document_type lo fija el service según el país."""

    country = serializers.CharField(write_only=True)

    amount_requested = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    monthly_income = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    class Meta:
        model = CreditApplication
        fields = [
            'country',
            'full_name',
            'document_number',
            'amount_requested',
            'monthly_income',
        ]

    def validate_country(self, value):
        code = value.strip().upper()
        if not Country.objects.filter(code=code, is_active=True).exists():
            raise serializers.ValidationError('País no soportado o inactivo.')
        return code


class CreditApplicationStatusSerializer(serializers.ModelSerializer):
    status = serializers.CharField()

    class Meta:
        model = CreditApplication
        fields = ['status']

    def validate_status(self, value):
        current = self.instance.status

        if current and current.is_terminal:
            raise serializers.ValidationError(
                f"El estado '{current.code}' es terminal y no acepta transiciones."
            )

        country = self.instance.country_ref
        target = CountryStatus.objects.filter(country=country, code=value).first()
        if target is None:
            raise serializers.ValidationError(
                f"Estado '{value}' no existe para este país."
            )

        if not StatusTransition.objects.filter(
            from_status=current, to_status=target
        ).exists():
            from_code = current.code if current else '—'
            raise serializers.ValidationError(
                f"Transición '{from_code}' → '{value}' no permitida."
            )

        return value


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStatusHistory
        fields = ['from_status', 'to_status', 'changed_by', 'changed_at', 'metadata']
        read_only_fields = fields


class CreditApplicationReadSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    country    = serializers.ReadOnlyField()
    status     = serializers.SerializerMethodField()
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = CreditApplication
        fields = [
            'id', 'user_email', 'country', 'full_name',
            'document_type', 'document_number',
            'amount_requested', 'monthly_income',
            'status', 'requested_at', 'updated_at',
            'status_history',
        ]

    def get_status(self, obj) -> str:
        return obj.status_code
