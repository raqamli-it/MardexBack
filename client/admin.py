from django.contrib import admin
from .models import Order, ClientNews, ClientTarif


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'gender', 'status', 'created_at')
    list_filter = ['gender', 'status', 'created_at']
    fields = ['id', 'job_category', 'job_id', 'desc', 'price', 'full_desc', 'city', 'region', 'gender', 'view_count', 'image']
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