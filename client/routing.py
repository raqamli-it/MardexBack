from django.urls import re_path
from client.consumers import UserOrderConsumer, OrderActionConsumer

websocket_urlpatterns = [
    re_path(r'ws/worker/$', UserOrderConsumer.as_asgi()),
    re_path(r'ws/clients/$', UserOrderConsumer.as_asgi()),
    re_path(r'ws/order-actions/$', OrderActionConsumer.as_asgi()),
    # re_path(r"ws/location/$", WorkerLocationConsumer.as_asgi()),
]
