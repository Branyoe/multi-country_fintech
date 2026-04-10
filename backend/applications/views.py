from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import CreditApplicationFilter
from .models import CreditApplication
from .serializers import (
    CreditApplicationSerializer,
    CreditApplicationStatusSerializer,
    CreditApplicationReadSerializer,
)
from .services import CreditApplicationService, BankProviderError


class CreditApplicationViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filterset_class = CreditApplicationFilter
    search_fields = ['full_name', 'document_number']
    ordering_fields = ['amount_requested', 'monthly_income', 'requested_at', 'updated_at', 'status', 'country']
    ordering = ['-requested_at']

    def get_queryset(self):
        return CreditApplication.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return CreditApplicationStatusSerializer
        if self.action in ('retrieve', 'list'):
            return CreditApplicationReadSerializer
        return CreditApplicationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = CreditApplicationService.create(
                serializer.validated_data, request.user
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except BankProviderError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(
            CreditApplicationReadSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        application = self.get_object()
        serializer = CreditApplicationStatusSerializer(
            application, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        application = CreditApplicationService.update_status(
            str(application.id),
            serializer.validated_data['status'],
            request.user.email,
        )
        return Response(CreditApplicationReadSerializer(application).data)


