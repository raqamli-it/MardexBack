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
        max_radius_km = max_radius_km or getattr(settings, "NEAREST_WORKER_MAX_RADIUS_KM", 30)
        order_lat = float(order.latitude)
        order_lon = float(order.longitude)

        workers_data = await sync_to_async(self._get_all_workers)()

        for radius in range(1, max_radius_km + 1):
            nearby_workers = []

            for worker in workers_data:
                if (
                    worker["role"] != "worker"
                    or worker["status"] != "idle"
                    or not worker["is_worker_active"]
                    or worker["job_category"] != order.job_category
                ):
                    continue

                if order.gender and worker["gender"] != order.gender:
                    continue

                distance = calculate_distance(
                    order_lat, order_lon,
                    float(worker["latitude"]), float(worker["longitude"])
                )

                if distance <= radius:
                    nearby_workers.append({**worker, "distance": distance})

            if nearby_workers:
                nearby_workers.sort(key=lambda w: w["distance"])
                return nearby_workers

        return []

    def _get_all_workers(self):
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
