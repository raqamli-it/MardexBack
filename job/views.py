from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from users.models import AbstractUser
from .models import CategoryJob, Job, City, Region
from .serializer import CategoryJobSerializer, JobSerializer, CitySerializer, RegionSerializer
from django.shortcuts import get_object_or_404


@api_view(['GET'])
def category_job_list(request):
    category_jobs = CategoryJob.objects.all()
    serializer = CategoryJobSerializer(category_jobs, many=True, context={'request': request})
    return Response(serializer.data)


class JobListByCategoryView(APIView):
    def get(self, request, pk):
        category_job = get_object_or_404(CategoryJob, id=pk)
        jobs = Job.objects.filter(category_job=category_job)
        category_serializer = CategoryJobSerializer(category_job, context={'request': request})
        jobs_serializer = JobSerializer(jobs, many=True, context={'request': request})

        result = category_serializer.data
        result['jobs'] = jobs_serializer.data

        return Response(result)


@api_view(['GET'])
def job_list(request):
    jobs = Job.objects.all()
    serializer = JobSerializer(jobs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def job_similar(request, pk):
    job = get_object_or_404(Job, pk=pk)
    serializer = JobSerializer(job, context={'request': request})
    return Response(serializer.data)



@api_view(['GET'])
def city_list(request):
    cities = City.objects.all()
    serializer = CitySerializer(cities, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def city_count(request):
    count = City.objects.count()
    return Response({"cities_count": count})


@api_view(['GET'])
def region_list(request):
    regions = Region.objects.all()
    serializer = RegionSerializer(regions, many=True, context={"request": request})
    return Response(serializer.data)


class RegionListByCityView(APIView):

    def get(self, request, pk):
        # Shaharning `id`si bo‘yicha City modelini topamiz
        city = get_object_or_404(City, id=pk)

        # Ushbu shaharga tegishli Regionlarni olish
        regions = Region.objects.filter(city_id=city)

        city_serializer = CitySerializer(city, context={'request': request})
        regions_serializer = RegionSerializer(regions, many=True, context={'request': request})

        result = city_serializer.data
        result['regions'] = regions_serializer.data

        return Response(result)



def get_filtered_workers(order, min_radius_km=None, max_radius_km=None):
    """
    Orderga mos workerlarni filter qilib,
    PostGIS yordamida eng yaqin workerlarni qaytaradi.
    """

    # Agar parametrlar kelsa ulardan foydalansin, kelmasa settings.py dagi defaultni olsin
    min_radius_km = min_radius_km or getattr(settings, "NEAREST_WORKER_MIN_RADIUS_KM", 1)
    max_radius_km = max_radius_km or getattr(settings, "NEAREST_WORKER_MAX_RADIUS_KM", 30)


    workers = AbstractUser.objects.filter(
        role='worker',
        status='idle',
        job_category=order.job_category,
        region=order.region,
        city=order.city,
        is_worker_active=True,
        point__isnull=False
    )

    if order.job_id.exists():
        workers = workers.filter(job_id__in=order.job_id.all()).distinct()

    if order.gender:
        workers = workers.filter(gender=order.gender)

    return workers.annotate(
        distance=Distance('point', order.point)
    ).filter(
        distance__gte=min_radius_km * 1000,
        distance__lte=max_radius_km * 1000
    ).order_by('distance')
