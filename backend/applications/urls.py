from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CountryListView, CreditApplicationViewSet

router = DefaultRouter()
router.register('', CreditApplicationViewSet, basename='applications')

urlpatterns = [
    path('countries/', CountryListView.as_view(), name='country-list'),
] + router.urls
