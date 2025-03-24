import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    @database_sync_to_async
    def get_user(self, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return User.objects.get(id=payload["user_id"])
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired.")
        except jwt.DecodeError:
            logger.warning("JWT decode error: Invalid token.")
        except User.DoesNotExist:
            logger.warning("User not found with given token.")
        return None

    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])
        auth_header = headers.get(b"authorization", b"").decode()

        if auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[-1]
            user = await self.get_user(token)
            scope["user"] = user if user else AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
