from rest_framework.routers import DefaultRouter
from .views import CreditApplicationViewSet

router = DefaultRouter()
router.register('', CreditApplicationViewSet, basename='applications')

urlpatterns = router.urls
