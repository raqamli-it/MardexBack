from django.urls import path
from . import views

urlpatterns = [
    path('category_jobs/', views.category_job_list, name='category_job_list'),  # Category job ro'yxati
    path('category_jobs/<int:pk>/', views.JobListByCategoryView.as_view(), name='category_job_recent'),  # Yangi category job'lar
    path('jobs/', views.job_list, name='job_list'),  # Job ro'yxati
    path('jobs/<int:pk>/similar/', views.job_similar, name='job_similar'),  # Job'ga o'xshash ishlar

    path('city/', views.city_list, name='city_list'),  # Shahar ro'yxati
    path('city/count/', views.city_count, name='city_count'),  # Shaharlar soni
    path('regions/', views.region_list, name='region_list'),  # Regionlar ro'yxati
    path('regions/<int:pk>/in_city/', views.RegionListByCityView.as_view(), name='region_in_city'),  # Regionlarni shaharga qarab filtrlaydi
]
