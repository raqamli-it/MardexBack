from django.urls import re_path
from client import consumers

websocket_urlpatterns = [
    re_path(r'ws/orders/(?P<worker_id>\d+)/$', consumers.OrderConsumer.as_asgi()),
]
