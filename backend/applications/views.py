from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import CreditApplication
from .serializers import (
    CreditApplicationSerializer,
    CreditApplicationStatusSerializer,
    CreditApplicationReadSerializer,
)


class CreditApplicationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = CreditApplication.objects.filter(user=self.request.user)
        country = self.request.query_params.get('country')
        if country:
            qs = qs.filter(country=country.upper())
        return qs

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return CreditApplicationStatusSerializer
        if self.action in ('retrieve', 'list'):
            return CreditApplicationReadSerializer
        return CreditApplicationSerializer
