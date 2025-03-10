from django.contrib import admin
from .models import Order, ClientNews, ClientTarif


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('client', 'worker', 'job_category', 'region', 'city', 'price', 'status', 'created_at')
    fields = ['client', 'worker', 'accepted_workers', 'job_category', 'job_id', 'city', 'region', 'price',
              'desc', 'full_desc', 'worker_count', 'gender', 'status', 'is_finish', 'latitude', 'longitude']
    ordering = ('created_at',)


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