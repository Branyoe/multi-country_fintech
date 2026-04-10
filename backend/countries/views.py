from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .cache import get_countries_cached


class CountryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        countries = get_countries_cached().values()
        data = [
            {
                'code': c.code,
                'label': c.label,
                'document_type': c.document_type,
                'document_hint': c.document_hint,
                'document_example': c.document_example,
                'document_regex': c.document_regex,
            }
            for c in countries
        ]
        return Response(data)
