import threading
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from client.models import Order
from client.serializer import OrderSerializer
from job.views import get_filtered_workers
import asyncio


class SendOrderToSelectedWorkersView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        order_id = request.data.get("order_id")
        worker_ids = request.data.get("worker_ids", [])

        try:
            order = Order.objects.get(id=order_id)

            if order.client != request.user:
                return Response({"detail": "Siz ushbu order egasi emassiz!"}, status=403)

            eligible_workers = get_filtered_workers(order)
            workers = eligible_workers.filter(id__in=worker_ids)

            channel_layer = get_channel_layer()

            for worker in workers:
                async_to_sync(channel_layer.group_send)(
                    f"worker_{worker.id}",
                    {
                        "type": "send_order_notification",
                        "order": OrderSerializer(order).data
                    }
                )

                order.notified_workers.add(worker)
                order.save()

                threading.Thread(
                    target=async_to_sync(auto_remove_worker),
                    args=(order, worker)
                ).start()

            return Response({"detail": "Tanlangan va mos keladigan workerlarga xabar yuborildi!"})

        except Order.DoesNotExist:
            return Response({"detail": "Order topilmadi!"}, status=404)


async def auto_remove_worker(order, worker, timeout=60):
    await asyncio.sleep(timeout)
    # Agar worker hali ham notified_workers ichida bo'lsa va hech qanday action bajarmagan bo'lsa
    notified_workers = await sync_to_async(lambda: list(order.notified_workers.all()))()
    if worker in notified_workers:
        await sync_to_async(order.notified_workers.remove)(worker)
        print(f"{worker.id}-dagi worker timeout bo'ldi va notified_workers dan o'chirildi.")

        worker.status = 'idle'
        await sync_to_async(worker.save)()

        if not await sync_to_async(order.notified_workers.exists)():
            order.status = 'stable'
            await sync_to_async(order.save)()

        print(f"Sending timeout notification to client ID: {order.client.id} for worker: {worker.full_name}")

        await get_channel_layer().group_send(
            f"user_{order.client.id}",
            {
                "type": "order_update",
                "order_id": order.id,
                "status": "timeout",
                "worker": worker.full_name
            }
        )

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from asgiref.sync import async_to_sync
# from channels.layers import get_channel_layer
# from client.models import Order
# from client.serializer import OrderSerializer
# from job.views import get_filtered_workers
#
#
# class SendOrderToSelectedWorkersView(APIView):
#     """ Client tanlagan workerlarga xabar yuborish (faqat filterdan o‘tganlar) """
#
#     def post(self, request, *args, **kwargs):
#         order_id = request.data.get("order_id")
#         worker_ids = request.data.get("worker_ids", [])
#
#         try:
#             order = Order.objects.get(id=order_id)
#             # Tanlangan workerlardan faqat filterdan o'tganlarini olamiz
#             eligible_workers = get_filtered_workers(order)
#             workers = eligible_workers.filter(id__in=worker_ids)
#
#             channel_layer = get_channel_layer()
#
#             for worker in workers:
#                 async_to_sync(channel_layer.group_send)(
#                     f"worker_{worker.id}",
#                     {
#                         "type": "send_order_notification",
#                         "order": OrderSerializer(order).data
#                     }
#                 )
#
#             return Response({"detail": "Tanlangan va mos keladigan workerlarga xabar yuborildi!"})
#
#         except Order.DoesNotExist:
#             return Response({"detail": "Order topilmadi!"}, status=404)
