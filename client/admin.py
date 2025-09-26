from django.contrib import admin

from users.models import ClientProfile
from .models import ClientNews, ClientTarif, OrderImage, Order
from django.contrib.gis import admin as gis_admin
from django import forms
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.admin import OSMGeoAdmin


class OrderImageInline(admin.TabularInline):
    model = OrderImage
    extra = 1
    max_num = 5  # limit to 5 images



@admin.register(Order)
class OrderAdmin(gis_admin.OSMGeoAdmin):  # OSMGeoAdmin ishlatamiz
    inlines = [OrderImageInline]
    list_display = ('id', 'client', 'worker', 'status', 'created_at', 'client_is_finished', 'get_finished_workers',)
    list_filter = ('status', 'job_category', 'created_at',)
    search_fields = ('client__username', 'worker__username', 'job_category__title')
    ordering = ('-created_at',)

    def get_finished_workers(self, obj):
        return obj.get_finished_workers()
    get_finished_workers.short_description = "Finished Workers"

    # Xarita o‘lchamlari
    map_width = 1100
    map_height = 600
    default_zoom = 15

    # Lat/Lon kiritish uchun input maydonlari
    formfield_overrides = {
        gis_models.PointField: {"widget": forms.TextInput(attrs={"placeholder": "lat, lon"})},
    }



@admin.register(ClientNews)
class ClientNewsAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'description')
    fields = ['description_uz', 'description_ru', 'description_en', 'image', ]
    ordering = ('created_at',)


@admin.register(ClientTarif)
class ClientTarifAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'top_limit', 'call_limit')
    fields = ['name', 'price', 'top_limit', 'call_limit',]
    search_fields = ('name',)


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "get_phone")
    search_fields = ("user__phone",)
    list_filter = ("user__role",)

    def get_phone(self, obj):
        return obj.user.phone
    get_phone.short_description = "Phone"
