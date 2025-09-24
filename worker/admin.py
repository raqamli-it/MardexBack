from django.contrib import admin

from users.models import WorkerProfile
from worker.models import WorkerNews, WorkerImage
from django.contrib.auth import get_user_model

User = get_user_model()


class WorkerImageInline(admin.TabularInline):
    model = WorkerImage
    extra = 1


@admin.register(User)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'status', 'role', 'gender', 'phone', 'is_superuser']
    list_filter = ['role', 'gender', 'region', 'city']
    search_fields = ['id', 'full_name_uz', 'phone',]
    fields = ['full_name_uz', 'full_name_ru', 'full_name_en',
              'description_uz', 'description_ru', 'description_en',
              'role', 'gender', 'latitude', 'longitude', 'status', 'is_worker_active',]
    inlines = [WorkerImageInline]


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