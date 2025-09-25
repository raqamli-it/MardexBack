from django.contrib import admin

from users.models import WorkerProfile
from worker.models import WorkerNews, WorkerImage
from django.contrib.auth import get_user_model, forms
from django.contrib.gis.admin import OSMGeoAdmin
from django import forms
from django.contrib.gis.db import models as gis_models


User = get_user_model()


class WorkerImageInline(admin.TabularInline):
    model = WorkerImage
    extra = 1


@admin.register(User)
class ProfileAdmin(OSMGeoAdmin):  # GIS xarita widgeti uchun OSMGeoAdmin ishlatamiz
    list_display = ['id', 'full_name', 'status', 'role', 'gender', 'phone', 'is_superuser']
    list_filter = ['role', 'gender', 'region', 'city']
    search_fields = ['id', 'full_name_uz', 'phone']
    fields = ['full_name_uz', 'full_name_ru', 'full_name_en',
              'description_uz', 'description_ru', 'description_en',
              'role', 'gender', 'point', 'status', 'is_worker_active']
    inlines = [WorkerImageInline]
    # Xarita o'lchamlari
    map_width = 10000  # kengligi px
    map_height = 400  # balandligi px
    default_lon = 69.2795532482657
    default_lat = 41.31127689979969
    default_zoom = 15


    # Lat/Lon kiritish uchun input maydonlari
    formfield_overrides = {
        gis_models.PointField: {"widget": forms.TextInput(attrs={"placeholder": "lat, lon"})},
    }
@admin.register(WorkerNews)
class WorkerNewsAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'description')
    fields = ['description_uz', 'description_ru', 'description_en', 'image',]
    ordering = ('created_at',)


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "get_phone")
    search_fields = ("user__phone",)
    list_filter = ("user__role",)

    def get_phone(self, obj):
        return obj.user.phone
    get_phone.short_description = "Phone"