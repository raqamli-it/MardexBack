from django.contrib.gis.geos import Point
from django.db import models
from job.models import CategoryJob, Job, Region, City
from users.models import AbstractUser
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.gis.db import models as gis_models

User = get_user_model()


class Order(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Erkak'),
        ('Female', 'Ayol'),
    ]

    STATUS_CHOICES = [
        ('stable', 'Stable'),
        ('success', 'Success'),
        ('in_progress', 'In_progress'),
        ('cancel_client', 'Cancel by Client'),
        ('cancel_worker', 'Cancel by Worker'),
    ]

    worker = models.ForeignKey(AbstractUser, on_delete=models.SET_NULL, blank=True, null=True,
                               related_name='orders_as_worker')
    accepted_workers = models.ManyToManyField(AbstractUser, related_name='accepted_orders', blank=True)
    rejected_workers = models.ManyToManyField(AbstractUser, related_name='rejected_workers', blank=True)
    notified_workers = models.ManyToManyField(AbstractUser, related_name='notified_orders', blank=True)
    finished_workers = models.ManyToManyField(User, related_name="finished_orders", blank=True)
    client = models.ForeignKey(AbstractUser, on_delete=models.SET_NULL, blank=True, null=True, related_name='client')
    job_category = models.ForeignKey(CategoryJob, on_delete=models.SET_NULL, blank=True, null=True)
    job_id = models.ManyToManyField(Job, blank=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    price = models.CharField(max_length=255, blank=True, null=True)
    desc = models.TextField(default="", blank=True, null=True)
    full_desc = models.TextField(default="", blank=True, null=True)
    worker_count = models.IntegerField(default=1)
    client_is_finished = models.BooleanField(default=False)
    worker_is_finished = models.BooleanField(default=False)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    view_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='stable'
    )
    # latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    # longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    point = gis_models.PointField(srid=4326, default=Point(69.279759, 41.311081))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.client} by {self.worker}"

    def get_finished_workers(self):
        return ", ".join([worker.full_name for worker in self.finished_workers.all()])


class OrderImage(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='client_image/', blank=True, null=True)

    def __str__(self):
        return f"Image for Order ID {self.order.id}"


class ClientReyting(models.Model):

    active_orders = models.PositiveIntegerField(default=0)  # Faol buyurtmalar soni
    completed_orders = models.PositiveIntegerField(default=0)  # Bajarilgan buyurtmalar soni
    cancelled_orders = models.PositiveIntegerField(default=0)  # Bekor qilingan buyurtmalar soni
    reyting = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(100.0)

        ], default=0.0,)


class ClientNews(models.Model):
    description = models.TextField()
    image = models.ImageField(upload_to='client/news_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ClientTarif(models.Model):
    name = models.CharField(max_length=100)  # Tarif nomi
    price = models.PositiveIntegerField(default=0)  # Tarif narxi
    top_limit = models.PositiveIntegerField(default=2)  # "Top" qilish limiti
    call_limit = models.PositiveIntegerField(default=3)  # "Vizov" qilish limiti

    def __str__(self):
        return f"{self.name} - {self.price} so'm"

    class Meta:
        verbose_name = "Client Tarif"
        verbose_name_plural = "Client Tariflar"


class TarifHaridi(models.Model):
    user = models.OneToOneField(
        AbstractUser,
        on_delete=models.CASCADE,
        null=True,
        related_name='client_harid')
    tarif_id = models.ForeignKey(ClientTarif, on_delete=models.CASCADE, null=True)
    status = models.BooleanField(default=True)
