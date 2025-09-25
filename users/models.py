import os
from django.contrib.gis.db import models as gis_models
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from job.models import Region, City, CategoryJob, Job


def image_create_time(instance, filename):
    current_date = timezone.now().strftime('%Y/%m/%d')
    base_filename, file_extension = os.path.splitext(filename)
    new_filename = f"{base_filename}_{timezone.now().strftime('%H%M%S')}{file_extension}"
    return f'passport_scans/{current_date}/{new_filename}'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, full_name, password=None, **extra_fields):
        if not phone:
            raise ValueError('The Phone field must be set')
        if not full_name:
            raise ValueError('The Full Name field must be set')

        user = self.model(phone=phone, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone, full_name, password, **extra_fields)


class AbstractUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('client', 'client'),
        ('worker', 'worker'),
    ]

    GENDER_CHOICES = [
        ('Male', 'Erkak'),
        ('Female', 'Ayol'),
    ]

    STATUS_CHOICES = [
        ('idle', 'Boʻsh'),
        ('working', 'Ishlayapti'),
        ('waiting_confirmation', 'Tasdiqlashni kutmoqda'),
        ('completed', 'Yakunlandi'),
        ('active', 'Faol'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, )
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='idle')
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    passport_scan = models.ImageField(upload_to=image_create_time, blank=True, null=True)
    passport_back_scan = models.ImageField(upload_to=image_create_time, blank=True, null=True)
    passport_scan_with_face = models.ImageField(upload_to=image_create_time, blank=True, null=True)
    passport_seria = models.CharField(max_length=50, blank=True, null=True)
    job_category = models.ForeignKey(CategoryJob, on_delete=models.SET_NULL, blank=True, null=True)
    job_id = models.ManyToManyField(Job, blank=True)

    avatar = models.ImageField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    reyting = models.FloatField(
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(100.0)
        ],
        default=0.0
    )
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_worker_active = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    point = gis_models.PointField(geography=True, null=True, blank=True)
    # latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    # longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['phone', 'full_name']

    def __str__(self):
        return f"{self.full_name} | {self.phone}"

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=["phone", "role"],
                name="unique_phone_role"
            )
        ]


class WorkerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_profile")

    def __str__(self):
        return f"Worker: {self.user.phone}"


class ClientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_profile")

    def __str__(self):
        return f"Client: {self.user.phone}"
