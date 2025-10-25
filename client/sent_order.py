import threading
import asyncio
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from client.models import Order
from client.serializer import OrderSerializer
from client.service import WorkerService


class SendOrderToSelectedWorkersView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        order_id = request.data.get("order_id")
        worker_ids = request.data.get("worker_ids", [])

        if not order_id:
            return Response({"detail": "order_id kiritilmagan!"}, status=400)

        # Orderni olish
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order topilmadi!"}, status=404)

        # Faqat o‘zining orderini yuborish huquqi
        if order.client != request.user:
            return Response({"detail": "Siz ushbu order egasi emassiz!"}, status=403)

        # Redis orqali mos workerlarni olish
        eligible_workers = WorkerService.get_eligible_workers(order)
        eligible_worker_ids = [int(w["id"]) for w in eligible_workers]

        # Client tanlagan va Redis orqali mos keladigan workerlarni kesish
        common_ids = set(map(int, worker_ids)) & set(eligible_worker_ids)
        if not common_ids:
            return Response({"detail": "Hech qanday mos worker topilmadi!"}, status=400)

        # Django modeli orqali olish
        selected_workers = User.objects.filter(id__in=common_ids, role="worker")[:20]

        if not selected_workers.exists():
            return Response({"detail": "Hech qanday worker topilmadi!"}, status=400)

        # WebSocket channel layer
        channel_layer = get_channel_layer()

        # Har bir worker uchun xabar yuborish
        for worker in selected_workers:
            try:
                # WebSocket orqali real-time xabar
                async_to_sync(channel_layer.group_send)(
                    f"worker_{worker.id}",
                    {
                        "type": "send_order_notification",
                        "order": OrderSerializer(order).data
                    }
                )

                # Worker'ni orderga bog‘lash
                order.notified_workers.add(worker)

                # Worker timeout mexanizmini ishga tushirish
                threading.Thread(
                    target=async_to_sync(auto_remove_worker),
                    args=(order, worker),
                    daemon=True  #  Thread avtomatik tozalanadi
                ).start()

            except Exception as e:
                print(f"[Xatolik] Worker {worker.id} ga xabar yuborishda muammo: {e}")

        order.save()

        return Response({
            "detail": f"{len(selected_workers)} ta workerga xabar yuborildi!",
            "workers": [w.id for w in selected_workers],
        })

async def auto_remove_worker(order, worker, timeout=60):
    """
    Worker agar 1 daqiqa ichida hech qanday harakat qilmasa,
    notified_workers dan o‘chirilib ketadi.
    """
    await asyncio.sleep(timeout)

    notified_ids = await sync_to_async(
        lambda: list(order.notified_workers.values_list("id", flat=True))
    )()

    if worker.id in notified_ids:
        await sync_to_async(order.notified_workers.remove)(worker)
        print(f" Worker {worker.id} timeout — notified_workers dan o‘chirildi.")

        worker.status = 'idle'
        await sync_to_async(worker.save)()

        # Agar boshqa active worker qolmagan bo‘lsa
        has_workers = await sync_to_async(order.notified_workers.exists)()
        if not has_workers:
            order.status = 'stable'
            await sync_to_async(order.save)()

# async def auto_remove_worker(order, worker, timeout=60):
#     """
#     Worker agar 1 daqiqa ichida hech qanday harakat qilmasa,
#     notified_workers dan o‘chirilib ketadi.
#     """
#     await asyncio.sleep(timeout)
#
#     notified_workers = await sync_to_async(lambda: list(order.notified_workers.all()))()
#
#     if worker in notified_workers:
#         await sync_to_async(order.notified_workers.remove)(worker)
#         print(f" Worker {worker.id} timeout bo‘ldi — notified_workers dan o‘chirildi.")
#
#         worker.status = 'idle'
#         await sync_to_async(worker.save)()
#
#         if not await sync_to_async(order.notified_workers.exists)():
#             order.status = 'stable'
#             await sync_to_async(order.save)()

        # Optional: client'ga timeout haqida bildirish
        # async_to_sync(channel_layer.group_send)(
        #     f"client_{order.client.id}",
        #     {"type": "timeout_notification", "worker_id": worker.id}
        # )





# import threading
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from asgiref.sync import async_to_sync, sync_to_async
# from channels.layers import get_channel_layer
# from client.models import Order
# from client.serializer import OrderSerializer
# from job.views import get_filtered_workers
# import asyncio
#
#
# class SendOrderToSelectedWorkersView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request, *args, **kwargs):
#         order_id = request.data.get("order_id")
#         worker_ids = request.data.get("worker_ids", [])
#
#         try:
#             order = Order.objects.get(id=order_id)
#
#             if order.client != request.user:
#                 return Response({"detail": "Siz ushbu order egasi emassiz!"}, status=403)
#
#             eligible_workers = get_filtered_workers(order)
#             workers = eligible_workers.filter(id__in=worker_ids)[:20]
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
#                 # print(f" Order {order.id} yuborildi -> worker_{worker.id}")  # <<< qo‘shing
#
#                 order.notified_workers.add(worker)
#                 order.save()
#
#                 threading.Thread(
#                     target=async_to_sync(auto_remove_worker),
#                     args=(order, worker)
#                 ).start()
#
#             return Response({"detail": "Tanlangan va mos keladigan workerlarga xabar yuborildi!"})
#
#         except Order.DoesNotExist:
#             return Response({"detail": "Order topilmadi!"}, status=404)
#
#
# async def auto_remove_worker(order, worker, timeout=60):
#     await asyncio.sleep(timeout)
#     # Agar worker hali ham notified_workers ichida bo'lsa va hech qanday action bajarmagan bo'lsa
#     notified_workers = await sync_to_async(lambda: list(order.notified_workers.all()))()
#     if worker in notified_workers:
#         await sync_to_async(order.notified_workers.remove)(worker)
#         print(f"{worker.id}-dagi worker timeout bo'ldi va notified_workers dan o'chirildi.")
#
#         worker.status = 'idle'
#         await sync_to_async(worker.save)()
#
#         if not await sync_to_async(order.notified_workers.exists)():
#             order.status = 'stable'
#             await sync_to_async(order.save)()
#
#         # print(f"Sending timeout notification to client ID: {order.client.id} for worker: {worker.full_name}")