import json
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.geos import Point
from client.models import Order
from django.contrib.auth import get_user_model
import redis.asyncio as aioredis
User = get_user_model()


class UserOrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", None)

        if not user or isinstance(user, AnonymousUser):
            await self.close()
            return

        path = self.scope["path"]  # example: /ws/orders/ or /ws/clients/
        user_role = getattr(user, "role", None)
        # print(user_role)

        if path.startswith("/ws/worker/") and user_role == "worker":
            self.room_group_name = f"worker_{user.id}"
            # print(" Worker qo‘shildi:", self.room_group_name)   # <<< shu yerga qo‘shasiz
        elif path.startswith("/ws/clients/") and user_role == "client":
            self.room_group_name = f"client_{user.id}"
            # print(" Client qo‘shildi:", self.room_group_name)   # <<< bu yerga ham
        else:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def order_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def send_order_notification(self, event):
        # print(" Worker consumer event keldi:", event)  # <-- test
        await self.send(text_data=json.dumps(event))


class OrderActionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = "order_action"
        self.user = await self.get_user_from_token()
        if not self.user:
            await self.close()
            return


        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
            await self.send(text_data=json.dumps({"debug": "Received request", "data": data}))

        except json.JSONDecodeError:
            return await self.send_error("Invalid JSON format")

        action = data.get("action")
        order_id = data.get("order_id")
        worker_ids = data.get('worker_ids', [])

        if not isinstance(order_id, int):
            return await self.send_error("Invalid or missing order_id")

        if action == "accept":
            await self.accept_order(order_id)
        elif action == "reject":
            await self.reject_order(order_id)
        elif action == "confirm":
            await self.confirm_order(order_id)
        elif action == "cancel":
            await self.cancel_order(order_id, worker_ids)
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

    async def send_update(self, user_ids, order_id, status, worker=None):
        for user_id in user_ids:
            message = {
                "type": "order_update",
                "order_id": order_id,
                "status": status,
            }
            if worker:
                if isinstance(worker, int):
                    # Faqat ID berilgan holat
                    message["worker_id"] = worker
                else:
                    # Worker obyekti berilgan holat
                    message["worker"] = {
                        "id": worker.id,
                        "full_name": worker.full_name,
                        "phone": worker.phone,
                        "image": worker.avatar.url if worker.avatar else None
                    }

            # print(f"Sending update to user_{user_id}: {message}")

            await self.channel_layer.group_send(
                f"client_{user_id}",
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
        worker = await self.get_worker(self.user.id)

        order = await self.get_order_with_client(order_id)
        if not order:
            await self.send(text_data=json.dumps({"error": "Order not found"}))
            return

        if order.status != "stable" and order.status != "in_progress":
            await self.send(text_data=json.dumps({"error": "Order is not available"}))
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

        await self.send_update([order.client.id], order.id,
                               order.status,
                               worker,
                               )

        await self.send(text_data=json.dumps({
            "message": "Order accepted",
            "order_status": order.status,
            "worker_status": worker.status
        }))

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

        if order.status == "stable" or (order.status == "in_progress" and not is_accepted):
            await sync_to_async(order.rejected_workers.add)(worker)
            await sync_to_async(order.notified_workers.remove)(worker)
            await sync_to_async(order.save)()
            await self.send_update([client.id], order.id, "rejected", worker.id)

            await self.send(text_data=json.dumps({"message": "Order rejected"}))
        else:
            await self.send(
                text_data=json.dumps({"error": "You have already accepted this order, you cannot reject it"}))

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

    async def cancel_order(self, order_id, worker_ids=None):
        try:
            order = await self.get_order_with_client(order_id)
            if not order:
                return await self.send_error("Order not found")

            if order.status != "in_progress":
                return await self.send_error("Order is not in cancellable status")

            workers = await sync_to_async(list)(order.accepted_workers.all())
            worker_ids_in_order = [w.id for w in workers]

            is_client = self.user == order.client
            current_worker = self.user if self.user.role == "worker" else None
            is_worker = bool(current_worker and current_worker.id in worker_ids_in_order)

            if not (is_client or is_worker):
                return await self.send_error("Permission denied")

            # Worker faqat o‘zini cancel qilishi kerak
            if is_worker:
                to_cancel = [w for w in workers if w.id == current_worker.id]
            elif is_client and worker_ids:
                to_cancel = [w for w in workers if w.id in worker_ids]
            else:
                return await self.send_error("Invalid request")

            if not to_cancel:
                return await self.send_error("No workers to cancel")

            # print(f"To Cancel List: {[w.id for w in to_cancel]}")

            for worker in to_cancel:
                await sync_to_async(order.accepted_workers.remove)(worker)
                worker.status = "idle"
                await self.save_worker(worker)

            remaining = await sync_to_async(list)(order.accepted_workers.all())
            if not remaining:
                order.status = "cancel_worker" if is_worker else "cancel_client"
                await self.save_order(order)

            if is_worker:
                await self.send_update(
                    [order.client.id],
                    order.id,
                    order.status,
                    worker_id=current_worker.id
                )
            # elif is_client:
            #     await self.send_update(
            #         [w.id for w in to_cancel],
            #         order.id,
            #         order.status
            #     )

            return await self.send_result({
                "cancelled": [w.id for w in to_cancel],
                "remaining": [w.id for w in remaining],
                "status": order.status,
                "initiator": "worker" if is_worker else "client"
            })

        except Exception as e:
            return await self.send_error(f"Error: {str(e)}")

    async def send_result(self, data):
        result = {"message": "Success", **data, "success": True}
        await self.send(text_data=json.dumps(result))
        return result


REDIS_URL = "redis://redis:6379"


class WorkerLocationConsumer(AsyncJsonWebsocketConsumer):
    redis = None  # Global Redis connection (class-level)

    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated or getattr(user, "role", None) != "worker":
            await self.close()
            return

        # Bitta umumiy Redis connection
        if not WorkerLocationConsumer.redis:
            WorkerLocationConsumer.redis = await aioredis.from_url(
                REDIS_URL,
                decode_responses=True,
                encoding="utf-8",
            )

        self.user = user
        await self.accept()
        full_name = await sync_to_async(lambda: self.user.full_name)()
        await self.send_json({"detail": f"Ulandi: {full_name}"})

    async def receive_json(self, content, **kwargs):
        lon = content.get("longitude")
        lat = content.get("latitude")

        if lon is None or lat is None:
            await self.send_json({"error": "Koordinatalar majburiy."})
            return

        try:
            lon = float(lon)
            lat = float(lat)
        except ValueError:
            await self.send_json({"error": "Koordinatalar noto‘g‘ri formatda."})
            return

        # Workerning to‘liq ma’lumotlarini olish (DB dan)
        user = await sync_to_async(lambda: self.user)()
        worker_data = {
            "id": user.id,
            "role": user.role,
            "status": user.status,
            "is_worker_active": getattr(user, "is_worker_active", True),
            "job_category": getattr(user, "job_category_id", None),
            "region": user.region,
            "city": user.city,
            "gender": user.gender,
            "latitude": lat,
            "longitude": lon,
        }

        key = f"worker:{user.id}"
        value = json.dumps(worker_data)

        # TTL ni o‘chiramiz → qiymat har doim mavjud bo‘ladi (agar update kelmasa ham)
        await WorkerLocationConsumer.redis.set(key, value)
        print(f" Redisga yozildi: {key} -> {value}")

        await self.send_json({
            "detail": "Joylashuv Redisda yangilandi!",
            "longitude": lon,
            "latitude": lat
        })

    async def disconnect(self, close_code):
        key = f"worker:{self.user.id}"
        data = await WorkerLocationConsumer.redis.get(key)
        if data:
            coords = json.loads(data)
            point = Point(coords["longitude"], coords["latitude"])
            await sync_to_async(self._save_point_to_db)(point)

    def _save_point_to_db(self, point):
        self.user.point = point
        self.user.save(update_fields=["point"])

# REDIS_URL = "redis://redis:6379"
#
# class WorkerLocationConsumer(AsyncJsonWebsocketConsumer):
#     redis = None  # Doimiy connection (klass darajasida)
#
#     async def connect(self):
#         user = self.scope["user"]
#
#         if not user.is_authenticated or getattr(user, "role", None) != "worker":
#             await self.close()
#             return
#
#         # Redis bilan bitta global ulanish
#         if not WorkerLocationConsumer.redis:
#             WorkerLocationConsumer.redis = await aioredis.from_url(
#                 REDIS_URL,
#                 decode_responses=True,
#                 encoding="utf-8",
#             )
#
#         self.user = user
#         await self.accept()
#         full_name = await sync_to_async(lambda: self.user.full_name)()
#         await self.send_json({"detail": f"Ulandi: {full_name}"})
#
#     async def receive_json(self, content, **kwargs):
#         lon = content.get("longitude")
#         lat = content.get("latitude")
#
#         if lon is None or lat is None:
#             await self.send_json({"error": "Koordinatalar majburiy."})
#             return
#
#         try:
#             lon = float(lon)
#             lat = float(lat)
#         except ValueError:
#             await self.send_json({"error": "Koordinatalar noto‘g‘ri formatda."})
#             return
#
#         key = f"worker_location:{self.user.id}"
#         value = json.dumps({"lon": lon, "lat": lat})
#
#         # Tez ishlaydigan Redis yozuvi (1 daqiqa TTL bilan)
#         await WorkerLocationConsumer.redis.set(key, value, ex=600)
#         print(f"✅ Redisga yozildi: {key} -> {value}")  # 👈 debug uchun
#
#         await self.send_json({
#             "detail": "Joylashuv Redisda yangilandi!",
#             "longitude": lon,
#             "latitude": lat
#         })
#
#     async def disconnect(self, close_code):
#         key = f"worker_location:{self.user.id}"
#         data = await WorkerLocationConsumer.redis.get(key)
#         if data:
#             coords = json.loads(data)
#             point = Point(coords["lon"], coords["lat"])
#             await sync_to_async(self._save_point_to_db)(point)
#
#     def _save_point_to_db(self, point):
#         self.user.point = point
#         self.user.save(update_fields=["point"])
