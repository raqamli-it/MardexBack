from .models import City, Region

from rest_framework import serializers
from .models import CategoryJob, Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'title_uz', 'title_ru', 'title_en', 'image', 'created_at']


class CategoryJobSerializer(serializers.ModelSerializer):
    jobs = JobSerializer(many=True, read_only=True)

    class Meta:
        model = CategoryJob
        fields = ['id', 'title_uz', 'title_ru', 'title_en', 'image', 'created_at', 'jobs']


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'title', ]


class CitySerializer(serializers.ModelSerializer):
    regions = RegionSerializer(many=True, read_only=True)

    class Meta:
        model = City
        fields = ['id', 'title', 'regions']

