from rest_framework import serializers
from django.core.validators import MinValueValidator
from countries.models import Country
from .models import CreditApplication


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
    class Meta:
        model = CreditApplication
        fields = ['status']

    def validate_status(self, value):
        current = self.instance.status
        allowed_transitions = {
            CreditApplication.Status.PENDING:      {CreditApplication.Status.UNDER_REVIEW, CreditApplication.Status.APPROVED, CreditApplication.Status.REJECTED},
            CreditApplication.Status.UNDER_REVIEW: {CreditApplication.Status.APPROVED, CreditApplication.Status.REJECTED},
            CreditApplication.Status.APPROVED:     set(),
            CreditApplication.Status.REJECTED:     set(),
        }
        if value not in allowed_transitions.get(current, set()):
            raise serializers.ValidationError(
                f"Cannot transition from '{current}' to '{value}'."
            )
        return value


class CreditApplicationReadSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    country = serializers.ReadOnlyField()

    class Meta:
        model = CreditApplication
        fields = [
            'id', 'user_email', 'country', 'full_name',
            'document_type', 'document_number',
            'amount_requested', 'monthly_income',
            'status', 'requested_at', 'updated_at',
        ]
