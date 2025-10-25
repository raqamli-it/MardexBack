# app/utils/redis_location_service.py

import json
from math import radians, sin, cos, sqrt, atan2
from django.conf import settings
from asgiref.sync import sync_to_async, async_to_sync
from django_redis import get_redis_connection


def calculate_distance(lat1, lon1, lat2, lon2):
    """Yer sharida ikki nuqta orasidagi masofa (km) — Haversine formulasi bilan"""
    R = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


class WorkerService:
    """Redis orqali workerlarni filtrlash uchun servis klass"""

    def __init__(self):
        self.redis = get_redis_connection("default")

    @classmethod
    def get_eligible_workers(cls, order):
        instance = cls()
        return async_to_sync(instance.get_filtered_workers)(order)

    async def get_filtered_workers(self, order, max_radius_km=None):
        """Order joylashuvi asosida yaqin workerlarni topish"""
        max_radius_km = max_radius_km or getattr(settings, "NEAREST_WORKER_MAX_RADIUS_KM", 30)

        # ✅ Agar order.point mavjud bo‘lsa undan olish, bo‘lmasa manual koordinata
        if hasattr(order, "point") and order.point:
            order_lon = float(order.point.x)
            order_lat = float(order.point.y)
        else:
            # fallback (serializerda longitude/latitude kelsa)
            order_lon = float(getattr(order, "longitude", 0))
            order_lat = float(getattr(order, "latitude", 0))

        workers_data = await sync_to_async(self._get_all_workers)()

        for radius in range(1, max_radius_km + 1):
            nearby_workers = []

            for worker in workers_data:
                if (
                    worker.get("role") != "worker"
                    or worker.get("status") != "idle"
                    or not worker.get("is_worker_active")
                    or worker.get("job_category") != order.job_category
                ):
                    continue

                if order.gender and worker.get("gender") != order.gender:
                    continue

                worker_lat = float(worker.get("latitude", 0))
                worker_lon = float(worker.get("longitude", 0))

                distance = calculate_distance(
                    order_lat, order_lon,
                    worker_lat, worker_lon
                )

                if distance <= radius:
                    nearby_workers.append({**worker, "distance": distance})

            if nearby_workers:
                nearby_workers.sort(key=lambda w: w["distance"])
                return nearby_workers

        return []

    def _get_all_workers(self):
        """Redis'dan barcha workerlarni JSON holatda olish"""
        workers = []
        for key in self.redis.scan_iter("worker:*"):
            data = self.redis.get(key)
            if not data:
                continue
            try:
                worker = json.loads(data)
                workers.append(worker)
            except json.JSONDecodeError:
                continue
        return workers


def get_user_location(user_id):
    """Redis'dan foydalanuvchi joylashuvini olish"""
    redis_conn = get_redis_connection("default")
    key = f"user_location_{user_id}"
    value = redis_conn.get(key)
    if value:
        return json.loads(value)
    return None
