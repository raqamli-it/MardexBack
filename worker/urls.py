from django.urls import path
from .views import WorkerRegistrationView, WorkerLoginView, WorkerPasswordChangeView, \
    JobListByCategoryView, categoryjob_list, UpdateUserJobView, OrderStatisticsAPIView, \
    WorkerProfileUpdateView, AddWorkerImageView, WorkerProfileDetailView, DeleteWorkerImagesView, \
    WorkerNewsDetailView
from .views import (RegionListByCityView, WorkerJobListView,
                    WorkerPhoneUpdateView, JobSearchAPIView, workernews_list)


urlpatterns = [
    path('register/', WorkerRegistrationView.as_view(), name='worker-register'),
    path('login/', WorkerLoginView.as_view(), name='worker-login'),
    path('password-change/', WorkerPasswordChangeView.as_view(), name='worker-password-change'),
    # path('websocket/', websocket_test, name='websocket_test'),

    path('categoryjob_list/', categoryjob_list, name='categoryjob_list'),
    path('category_jobs/<int:pk>/', JobListByCategoryView.as_view(), name='jobs_by_category'),

    # worker ishni update va get qilishi uchun  va update qilingan ishlarini get qilish uchun url
    path('update_user_job/', UpdateUserJobView.as_view(), name='jobs_by_category'),
    path('user_job/', WorkerJobListView.as_view(), name='user_job'),  # Profilni ko‘rish uchun API

    # worker profil uchun statistika yani atmen qilingan joblar soni
    path('order-statistics/', OrderStatisticsAPIView.as_view(), name='order-statistics'),

    # har bir worker o'zini ro'yxatdan o'tgan raqamini upfate qilishi uchun url
    path('api/worker/update-phone/', WorkerPhoneUpdateView.as_view(), name='worker-update-phone'),

    # shaharga tegishli regionlarni filter qilamiz shu url orqali
    path('api/city/<int:pk>/', RegionListByCityView.as_view(), name='region-list-by-city'),

    # worker job va category ichidan search qilishi uchun url
    path('worker-job-search/', JobSearchAPIView.as_view(), name='job-search'),

    # worker uchun news
    path('workernews/', workernews_list),
    path('workernews/<int:pk>/', WorkerNewsDetailView.as_view(), name='workernews-detail'),


    # har bir worker o'zini profil uchun malumotlarini korishi uchun
    path('workers/detail/', WorkerProfileDetailView.as_view(), name='worker-profile-list'),
    # Har bir worker o'zini profilini malumotlarini Update Worker Profile
    path('workers/profile/update/', WorkerProfileUpdateView.as_view(), name='worker-profile-update'),
    # Add Worker Image
    path('workers/profile/add-image/', AddWorkerImageView.as_view(), name='add-worker-image'),


    # worker imagelarini 2 ta yoki 3 tagacha tanlab bittada delete qilish uchun url
    path('delete-images/', DeleteWorkerImagesView.as_view(), name='delete-images'),

]
