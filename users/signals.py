# users/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.gis.geos import Point

from client.models import Order
from .models import AbstractUser


@receiver(pre_save, sender=AbstractUser)
def set_worker_location(sender, instance, **kwargs):
    if instance.latitude and instance.longitude:
        instance.location = Point(float(instance.longitude), float(instance.latitude), srid=4326)

@receiver(pre_save, sender=Order)
def set_order_location(sender, instance, **kwargs):
    if instance.latitude and instance.longitude:
        instance.location = Point(float(instance.longitude), float(instance.latitude), srid=4326)
