import json

from channels.generic.websocket import AsyncWebsocketConsumer


class OrderConsumer(AsyncWebsocketConsumer):
    """Faqat tegishli workerlarga yangi order haqida xabar yuborish"""

    async def connect(self):
        """Worker-lar o‘ziga tegishli kanalga qo‘shiladi"""
        self.worker_id = self.scope['url_route']['kwargs']['worker_id']
        self.worker_room = f"worker_{self.worker_id}"
        await self.channel_layer.group_add(self.worker_room, self.channel_name)
        print(f"🔗 CONNECTING: {self.channel_name} -> {self.worker_room}")

        await self.accept()

    async def disconnect(self, close_code):
        """Worker kanalni tark etganda"""
        if hasattr(self, 'worker_room'):
            await self.channel_layer.group_discard(self.worker_room, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Client-lardan keladigan xabarlar (bu yerda ishlatmaymiz)"""
        await self.send(text_data=json.dumps({"message": "Bu bildirishnoma kanali"}))

    async def send_order_notification(self, event):
        """Yangi order haqida xabar yuborish"""
        await self.send(text_data=json.dumps(event))
