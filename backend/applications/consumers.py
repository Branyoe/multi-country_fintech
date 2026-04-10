from urllib.parse import parse_qs
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import CreditApplication


class ApplicationTimelineConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        application_id = self.scope['url_route']['kwargs'].get('application_id', '')
        if not _is_valid_uuid(application_id):
            await self.close(code=4400)
            return

        token = self._extract_token_from_query()
        if not token:
            await self.close(code=4401)
            return

        user = await _authenticate_user(token)
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        has_access = await _user_owns_application(user.id, application_id)
        if not has_access:
            await self.close(code=4403)
            return

        self.group_name = f'application_{application_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        group_name = getattr(self, 'group_name', None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def timeline_event(self, event: dict) -> None:
        await self.send_json(event['data'])

    def _extract_token_from_query(self) -> str:
        query = parse_qs(self.scope.get('query_string', b'').decode())
        return query.get('token', [''])[0].strip()


@database_sync_to_async
def _authenticate_user(token: str):
    auth = JWTAuthentication()
    try:
        validated = auth.get_validated_token(token)
        return auth.get_user(validated)
    except (InvalidToken, TokenError):
        return None


@database_sync_to_async
def _user_owns_application(user_id, application_id: str) -> bool:
    return CreditApplication.objects.filter(id=application_id, user_id=user_id).exists()


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (TypeError, ValueError):
        return False
