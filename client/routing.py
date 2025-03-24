from django.urls import re_path
from client import consumers
from client.consumers import ClientConsumer

websocket_urlpatterns = [
    re_path(r'ws/orders/(?P<worker_id>\d+)/$', consumers.OrderConsumer.as_asgi()),
    re_path(r'ws/order-actions/$', consumers.OrderActionConsumer.as_asgi()),
    re_path(r'ws/clients/(?P<client_id>\d+)/$', ClientConsumer.as_asgi()),
]
