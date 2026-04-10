from django.urls import re_path

from .consumers import ApplicationTimelineConsumer


websocket_urlpatterns = [
    re_path(
        r'^ws/applications/(?P<application_id>[0-9a-f-]+)/timeline/$',
        ApplicationTimelineConsumer.as_asgi(),
    ),
]
