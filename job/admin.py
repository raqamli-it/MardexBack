from django.contrib import admin
from .models import CategoryJob, Job, City, Region


@admin.register(CategoryJob)
class CategoryJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_at')
    search_fields = ('title',)
    fields = ['title_uz', 'title_ru', 'title_en', 'image']
    ordering = ('created_at',)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category_job', 'created_at')
    search_fields = ('title',)
    fields = ['title_uz', 'title_ru', 'title_en', 'category_job',]
    ordering = ('created_at',)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('id', 'title',)
    search_fields = ('title',)
    fields = ['title' 'regions']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title',)
    search_fields = ('title',)
    fields = ['title', 'city_id']
    ordering = ('title',)


