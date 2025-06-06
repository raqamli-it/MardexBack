from django.contrib import admin
from .models import Order, ClientNews, ClientTarif, OrderImage


class OrderImageInline(admin.TabularInline):
    model = OrderImage
    extra = 1
    max_num = 5  # limit to 5 images




@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderImageInline]
    list_display = ('id', 'client', 'worker', 'status', 'created_at', 'client_is_finished', 'get_finished_workers',)
    list_filter = ('status', 'job_category', 'created_at',)
    search_fields = ('client__username', 'worker__username', 'job_category__title')
    ordering = ('-created_at',)

    def get_finished_workers(self, obj):
        return obj.get_finished_workers()

    get_finished_workers.short_description = "Finished Workers"


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