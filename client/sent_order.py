from rest_framework.views import APIView
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from client.models import Order
from job.views import get_filtered_workers


class SendOrderToSelectedWorkersView(APIView):
    """ Client tanlagan workerlarga xabar yuborish (faqat filterdan o‘tganlar) """

    def post(self, request, *args, **kwargs):
        order_id = request.data.get("order_id")
        worker_ids = request.data.get("worker_ids", [])

        try:
            order = Order.objects.get(id=order_id)
            # Tanlangan workerlardan faqat filterdan o'tganlarini olamiz
            eligible_workers = get_filtered_workers(order)
            workers = eligible_workers.filter(id__in=worker_ids)

            channel_layer = get_channel_layer()

            for worker in workers:
                async_to_sync(channel_layer.group_send)(
                    f"worker_{worker.id}",
                    {
                        "type": "send_order_notification",
                        "order_id": order.id,
                        "job_category": order.job_category.id if order.job_category else None,
                        "job_id": list(order.job_id.values_list("id", flat=True)),
                        "desc": order.desc,
                        "price": order.price,
                        "region": order.region.id if order.region else None,
                        "city": order.city.id if order.city else None,
                        "client": str(order.client) if order.client else None,
                        "created_at": order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                )

            return Response({"detail": "Tanlangan va mos keladigan workerlarga xabar yuborildi!"})

        except Order.DoesNotExist:
            return Response({"detail": "Order topilmadi!"}, status=404)
