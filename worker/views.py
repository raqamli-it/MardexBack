from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.generics import UpdateAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated  # Foydalanuvchi autentifikatsiyasi
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

from client.models import Order
from job.models import Job, CategoryJob
from job.serializer import JobSerializer, CategoryJobSerializer
from .models import WorkerNews, WorkerImage
from .serializers import WorkerRegistrationSerializer, WorkerLoginSerializer, \
    WorkerPasswordChangeSerializer, UserUpdateSerializer, \
    WorkerImageSerializer, WorkerJobSerializer, WorkerPhoneUpdateSerializer, WorkerNewsSerializer, \
    WorkerUpdateSerializer, WorkerImageDeleteSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from users.models import AbstractUser
from django.contrib.auth import get_user_model
from job.models import City, Region
from .serializers import CitySerializer, RegionSerializer

User = get_user_model()

# registratsiya qismi class
class WorkerRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = WorkerRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        worker = serializer.save()

        refresh = RefreshToken.for_user(worker)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


# login class
class WorkerLoginView(generics.GenericAPIView):
    serializer_class = WorkerLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        worker = serializer.validated_data

        refresh = RefreshToken.for_user(worker)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "worker": WorkerRegistrationSerializer(worker).data,
        }, status=status.HTTP_200_OK)


# parol change class
class WorkerPasswordChangeView(generics.GenericAPIView):
    serializer_class = WorkerPasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Password updated successfully."})

    def perform_update(self, serializer):
        serializer.save()


# category bo'yicha job larni filterlash
class JobListByCategoryView(APIView):
    def get(self, request, pk):
        category_job = get_object_or_404(CategoryJob, id=pk)
        jobs = Job.objects.filter(category_job=category_job)
        category_serializer = CategoryJobSerializer(category_job, context={'request': request})
        jobs_serializer = JobSerializer(jobs, many=True, context={'request': request})

        result = category_serializer.data
        result['jobs'] = jobs_serializer.data

        return Response(result)


# worker uchun tangalagan ishlarini upfate va get qilish uchun classlar
class UpdateUserJobView(UpdateAPIView):
    queryset = AbstractUser.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Foydalanuvchi faqat o'zini yangilashi mumkin
        return self.request.user


class WorkerJobListView(RetrieveAPIView):
    queryset = AbstractUser.objects.select_related('job_category').prefetch_related('job_id')  # Optimallashtirish
    serializer_class = WorkerJobSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user  # Faqat kirgan foydalanuvchining ma'lumotlarini qaytaradi


# ishlarni categoriyasi uchun list
@api_view(['GET'])
def categoryjob_list(request):
    category_jobs = CategoryJob.objects.all()
    serializer = CategoryJobSerializer(category_jobs, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# worker profilini statistikasi yani nechta odam atmen qilganligi
class OrderStatisticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        total_orders = Order.objects.filter(worker=user).count()
        success_orders = Order.objects.filter(worker=user, status='success').count()
        cancel_client_orders = Order.objects.filter(worker=user, status='cancel_client').count()

        # Natijalarni JSON formatida qaytarish
        return Response({
            "total_orders": total_orders,
            "success_orders": success_orders,
            "cancel_client_orders": cancel_client_orders,
        })


# workerlar har biri o'zini telefon raqamini update qilishshi uchun views
class WorkerPhoneUpdateView(generics.GenericAPIView):
    serializer_class = WorkerPhoneUpdateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Phone number updated successfully."}, status=status.HTTP_200_OK)


# shaharga tegishli regionlarni filter qilamiz shu url orqali
class RegionListByCityView(APIView):

    def get(self, request, pk):
        # Shaharning `id`si bo‘yicha City modelini topamiz
        city = get_object_or_404(City, id=pk)

        # Ushbu shaharga tegishli Regionlarni olish
        regions = Region.objects.filter(city_id=city)

        # Serializerlar bilan ma'lumotlarni formatlaymiz
        city_serializer = CitySerializer(city, context={'request': request})
        regions_serializer = RegionSerializer(regions, many=True, context={'request': request})

        # Natijani birlashtirib qaytaramiz
        result = city_serializer.data
        result['regions'] = regions_serializer.data

        return Response(result)


# category va job ichidan search qiladi
class JobSearchAPIView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')

        if not query:
            return Response({"error": "Qidiruv so'rovini kiriting (q)"}, )

        # Harflar bo'yicha qidiruv
        categories = CategoryJob.objects.filter(title__icontains=query)
        jobs = Job.objects.filter(Q(title__icontains=query) | Q(category_job__title__icontains=query))

        category_serializer = CategoryJobSerializer(categories, many=True, context={'request': request})
        job_serializer = JobSerializer(jobs, many=True, context={'request': request})

        return Response({
            "categories": category_serializer.data,
            "jobs": job_serializer.data
        })


@api_view(['GET'])
def workernews_list(request):
    news = WorkerNews.objects.all()
    serializer = WorkerNewsSerializer(news, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# har bir worker o'zini profilini get qiladi token bilan farqlanadi
class WorkerProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        worker = request.user
        serializer = WorkerUpdateSerializer(worker, context={'request': request})
        return Response(serializer.data)


# har bir worker o'zini profilini malumotlarini update qilishi uchun
class WorkerProfileUpdateView(UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = WorkerUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# har bir worker o'zini profili uchun 5 tagacha rasm qo'shishi uchun
class AddWorkerImageView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Fetching the authenticated user
        profile = request.user

        # Ensure the user doesn't exceed the 5 image limit
        if profile.profileimage.count() >= 5:
            return Response({"error": "5 tadan ortiq tasvir qo'shib bo'lmaydi."}, status=status.HTTP_400_BAD_REQUEST)

        # Save the new image
        serializer = WorkerImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# har bir worker o'zini profilidagi 5 ta gacha qo'shadigan rasmlarini hohlaganini tanlab delete qiladi
class DeleteWorkerImagesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = WorkerImageDeleteSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Rasmlarni o'chirish
            deleted_images = serializer.delete_images(request.user, serializer.validated_data['image_ids'])
            return Response(
                {"message": f"{len(deleted_images)} ta rasm muvaffaqiyatli o'chirildi."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkerNewsDetailView(APIView):
    def get(self, request, pk):
        worker_news = get_object_or_404(WorkerNews, pk=pk)
        serializer = WorkerNewsSerializer(worker_news, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)