import json
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from client.models import Order
from django.contrib.auth import get_user_model

User = get_user_model()


class OrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", None)

        if not user or isinstance(user, AnonymousUser):
            await self.close()
            return

        self.worker_id = self.scope["url_route"]["kwargs"]["worker_id"]

        if not await self.is_valid_worker(user, self.worker_id):
            await self.close()
            return

        self.worker_room = f"worker_{self.worker_id}"
        await self.channel_layer.group_add(self.worker_room, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "worker_room"):
            await self.channel_layer.group_discard(self.worker_room, self.channel_name)

    async def send_order_notification(self, event):
        await self.send(text_data=json.dumps(event))

    async def order_update(self, event):
        await self.send(text_data=json.dumps({
            "order_id": event["order_id"],
            "status": event["status"]
        }))

    @database_sync_to_async
    def is_valid_worker(self, user, worker_id):
        return str(user.id) == str(worker_id)


class ClientConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get('user', None)
        if not user or isinstance(user, AnonymousUser):
            await self.close()
            return

        self.client_id = self.scope["url_route"]["kwargs"]["client_id"]

        if not await self.is_valid_client(user, self.client_id):
            await self.close()
            return

        self.client_room = f"user_{self.client_id}"
        await self.channel_layer.group_add(self.client_room, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "client_room"):
            await self.channel_layer.group_discard(self.client_room, self.channel_name)

    async def order_update(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def is_valid_client(self, user, client_id):
        return str(user.id) == str(client_id)


class OrderActionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = await self.get_user_from_token()
        if not self.user:
            await self.close()
            return

        self.room_name = "order_action"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return await self.send_error("Invalid JSON format")

        action = data.get("action")
        order_id = data.get("order_id")

        if not isinstance(order_id, int):
            return await self.send_error("Invalid or missing order_id")

        if action == "accept":
            await self.accept_order(order_id)
        elif action == "reject":
            await self.reject_order(order_id)
        elif action == "confirm":
            await self.confirm_order(order_id)
        elif action == "cancel":
            await self.cancel_order(order_id)
        else:
            await self.send_error("Invalid action")

    async def get_user_from_token(self):
        query_string = self.scope["query_string"].decode()
        token = dict(x.split("=") for x in query_string.split("&")).get("token")
        if not token:
            return None

        try:
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            return await self.get_user(access_token["user_id"])
        except Exception:
            return None

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    async def send_error(self, message):
        await self.send(text_data=json.dumps({"error": message}))

    async def send_update(self, user_ids, order_id, status, worker_id=None):
        for user_id in user_ids:
            message = {
                "type": "order_update",
                "order_id": order_id,
                "status": status,
            }
            if worker_id:
                message["worker_id"] = worker_id

            print(f"Sending update to user_{user_id}: {message}")

            await self.channel_layer.group_send(
                f"user_{user_id}",
                message
            )

    @sync_to_async
    def get_order_with_client(self, order_id):
        return Order.objects.select_related("client").filter(id=order_id).first()

    @sync_to_async
    def get_worker(self, worker_id):
        try:
            return User.objects.filter(id=worker_id, role="worker").first()
        except User.DoesNotExist:
            return None

    @sync_to_async
    def remove_notified_worker(self, order, worker):
        order.notified_workers.remove(worker)

    @sync_to_async
    def add_accepted_worker(self, order, worker):
        order.accepted_workers.add(worker)

    @sync_to_async
    def save_order(self, order):
        order.save()

    @sync_to_async
    def save_worker(self, worker):
        worker.save()

    async def accept_order(self, order_id):
        try:
            order = await self.get_order_with_client(order_id)
            if not order:
                await self.send(text_data=json.dumps({"error": "Order not found"}))
                return
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))
            return

        if order.status != "stable" and order.status != "in_progress":
            await self.send(text_data=json.dumps({"error": "Order is not available for acceptance"}))
            return

        worker = self.user
        client = order.client

        if not worker:
            await self.send(text_data=json.dumps({"error": "Worker not found"}))
            return

        if worker.status != "idle":
            await self.send(text_data=json.dumps({"error": "Worker is not available"}))
            return

        await self.remove_notified_worker(order, worker)

        await self.add_accepted_worker(order, worker)

        if order.status == "stable":
            order.status = "in_progress"

        worker.status = "working"

        await self.save_order(order)
        await self.save_worker(worker)

        await self.send_update([client.id], order.id, order.status, worker.id)

        await self.send(text_data=json.dumps(
            {
                "message": "Order accepted",
                "order_status": order.status,
                "worker_status": worker.status
            }
        ))

    async def reject_order(self, order_id):
        try:
            order = await self.get_order_with_client(order_id)
            if not order:
                await self.send(text_data=json.dumps({"error": "Order not found"}))
                return
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))
            return

        worker = self.user
        client = order.client

        if not worker:
            await self.send(text_data=json.dumps({"error": "Worker not found"}))
            return

        notified_workers = await sync_to_async(lambda: list(order.notified_workers.all()))()

        # Faqat aynan shu order uchun accepted_workers tekshiramiz
        is_accepted = await sync_to_async(lambda: worker in order.accepted_workers.all())()

        if worker not in notified_workers:
            await self.send(text_data=json.dumps({"error": "Worker was not notified or already responded"}))
            return

        # Faqat shu order bo‘yicha worker accepted bo‘lgan bo‘lsa reject qila olmaydi
        if order.status == "stable" or (order.status == "in_progress" and not is_accepted):
            await sync_to_async(order.rejected_workers.add)(worker)
            await sync_to_async(order.notified_workers.remove)(worker)
            await sync_to_async(order.save)()
            await self.send_update([client.id], order.id, "rejected", worker.id)

            await self.send(text_data=json.dumps({"message": "Order rejected"}))
        else:
            await self.send(text_data=json.dumps({"error": "You have already accepted this order, you cannot reject it"}))

    async def confirm_order(self, order_id):
        try:
            order = await self.get_order_with_client(order_id)
            if not order:
                await self.send(text_data=json.dumps({"error": "Order not found"}))
                return
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))
            return

        if order.status != "in_progress":
            await self.send(text_data=json.dumps({"error": "Order is not available for confirmation"}))
            return

        user = self.user
        client = order.client
        accepted_workers = await sync_to_async(lambda: list(order.accepted_workers.all()))()
        finished_workers = await sync_to_async(lambda: list(order.finished_workers.all()))()

        if user == client:
            order.client_is_finished = True
        elif user in accepted_workers:
            if user not in finished_workers:
                await sync_to_async(order.finished_workers.add)(user)
        else:
            await self.send(text_data=json.dumps({"error": "You are not part of this order"}))
            return

        await self.save_order(order)

        finished_workers = await sync_to_async(lambda: list(order.finished_workers.all()))()

        all_workers_finished = set(finished_workers) == set(accepted_workers)
        if all_workers_finished and order.client_is_finished:
            order.status = "success"
            await self.save_order(order)
            await self.send_update([client.id], order.id, order.status)

            for worker in finished_workers:
                worker.status = "idle"
                await self.save_worker(worker)

        await self.send(text_data=json.dumps({
            "message": "Order confirmed",
            "client_is_finished": order.client_is_finished,
            "worker_is_finished": [worker.id for worker in finished_workers],
            "order_status": order.status
        }))


# import json
#
# from channels.generic.websocket import AsyncWebsocketConsumer
#
#
# class OrderConsumer(AsyncWebsocketConsumer):
#     """Faqat tegishli workerlarga yangi order haqida xabar yuborish"""
#
#     async def connect(self):
#         """Worker-lar o‘ziga tegishli kanalga qo‘shiladi"""
#         self.worker_id = self.scope['url_route']['kwargs']['worker_id']
#         self.worker_room = f"worker_{self.worker_id}"
#         await self.channel_layer.group_add(self.worker_room, self.channel_name)
#
#         await self.accept()
#
#     async def disconnect(self, close_code):
#         """Worker kanalni tark etganda"""
#         if hasattr(self, 'worker_room'):
#             await self.channel_layer.group_discard(self.worker_room, self.channel_name)
#
#     async def send_order_notification(self, event):
#         """Yangi order haqida xabar yuborish"""
#         await self.send(text_data=json.dumps(event))
