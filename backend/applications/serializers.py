from rest_framework import serializers
from django.core.validators import MinValueValidator
from .models import CreditApplication


class CreditApplicationSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

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
            'id', 'user', 'country', 'full_name',
            'document_type', 'document_number',
            'amount_requested', 'monthly_income',
            'status', 'requested_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'requested_at', 'updated_at']

    def validate(self, attrs):
        country = attrs.get('country')
        document_type = attrs.get('document_type')
        expected = CreditApplication.COUNTRY_DOCUMENT_MAP.get(country)

        if expected and document_type != expected:
            raise serializers.ValidationError({
                'document_type': (
                    f'{country} requires {expected}, got {document_type}.'
                )
            })
        return attrs


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

    class Meta:
        model = CreditApplication
        fields = [
            'id', 'user_email', 'country', 'full_name',
            'document_type', 'document_number',
            'amount_requested', 'monthly_income',
            'status', 'requested_at', 'updated_at',
        ]
