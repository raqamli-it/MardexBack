from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.generics import UpdateAPIView, RetrieveAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission  # Foydalanuvchi autentifikatsiyasi
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q, Case, IntegerField, When

from client.models import Order
from client.serializer import OrderSerializer
from job.models import Job, CategoryJob
from job.serializer import JobSerializer, CategoryJobSerializer
from .models import WorkerNews
from .serializers import WorkerRegistrationSerializer, WorkerLoginSerializer, \
    WorkerPasswordChangeSerializer, UserUpdateSerializer, \
    WorkerImageSerializer, WorkerJobSerializer, WorkerPhoneUpdateSerializer, WorkerNewsSerializer, \
    WorkerUpdateSerializer, WorkerImageDeleteSerializer, WorkerActiveSerializer, WorkerLocationUpdateSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from users.models import AbstractUser
from django.contrib.auth import get_user_model
from job.models import City, Region
from .serializers import CitySerializer, RegionSerializer

User = get_user_model()


class WorkerRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = WorkerRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        worker = serializer.save()

        refresh = RefreshToken.for_user(worker)
        refresh['role'] = worker.role

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "worker": WorkerRegistrationSerializer(worker).data
        }, status=status.HTTP_201_CREATED)


class WorkerLoginView(generics.GenericAPIView):
    serializer_class = WorkerLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        worker = serializer.validated_data

        if worker.role != 'worker':
            return Response({"error": "Only workers can login here."}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(worker)
        refresh['role'] = worker.role

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "worker": WorkerRegistrationSerializer(worker).data,
        }, status=status.HTTP_200_OK)



class IsWorker(BasePermission):
    def has_permission(self, request, view):
        # Tokendagi rolni tekshirish
        token = request.auth
        if token:
            return token.get('role') == 'worker'
        return False


class WorkerPasswordChangeView(generics.GenericAPIView):
    serializer_class = WorkerPasswordChangeSerializer
    permission_classes = [IsAuthenticated,  IsWorker]

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
# class OrderStatisticsAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request, *args, **kwargs):
#         user = request.user
#         total_orders = Order.objects.filter(worker=user).count()
#         success_orders = Order.objects.filter(worker=user, status='success').count()
#         cancel_client_orders = Order.objects.filter(worker=user, status='cancel_client').count()
#
#         # Natijalarni JSON formatida qaytarish
#         return Response({
#             "total_orders": total_orders,
#             "success_orders": success_orders,
#             "cancel_client_orders": cancel_client_orders,
#         })


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
        city = get_object_or_404(City, id=pk)
        regions = Region.objects.filter(city_id=city)
        city_serializer = CitySerializer(city, context={'request': request})
        regions_serializer = RegionSerializer(regions, many=True, context={'request': request})

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


class WorkerActiveView(APIView):
    authentication_classes = []  # Avto-auth o‘chiriladi
    permission_classes = []      # Permission ham

    def authenticate_user(self, request):
        jwt_authenticator = JWTAuthentication()
        try:
            user, validated_token = jwt_authenticator.authenticate(request)
            return user
        except Exception:
            return None

    def get(self, request):
        user = self.authenticate_user(request)
        if not user:
            return Response({"detail": "Invalid or missing token"}, status=status.HTTP_401_UNAUTHORIZED)

        if user.role != "worker":
            return Response({"detail": "Only workers can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)

        serializer = WorkerActiveSerializer(user)
        return Response(serializer.data)

    def post(self, request):
        user = self.authenticate_user(request)
        if not user:
            return Response({"detail": "Invalid or missing token"}, status=status.HTTP_401_UNAUTHORIZED)

        if user.role != "worker":
            return Response({"detail": "Only workers can update this."}, status=status.HTTP_403_FORBIDDEN)

        serializer = WorkerActiveSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class WorkerPublicOrdersView(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    # permission_classes = [AllowAny]  # Token talab qilinmaydi

    def get_queryset(self):
        worker_id = self.kwargs.get("worker_id")
        return Order.objects.filter(
            accepted_workers__id=worker_id,
            status__in=['in_progress', 'success']  # 1-chi talab
        ).order_by(
            Case(  # 2-chi talab: in_progress oldinda
                When(status='in_progress', then=0),
                When(status='success', then=1),
                default=2,
                output_field=IntegerField()
            ),
            '-id'  # Har bir status ichida oxirgilar birinchi chiqadi
        )



# class WorkerOrderHistoryView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         worker = request.user
#
#         # Avval faol orderlar
#         active_orders = Order.objects.filter(
#             accepted_workers=worker,
#             status__in=['stable', 'in_progress']
#         )
#
#         # So'ngra yakunlanganlar
#         completed_orders = Order.objects.filter(
#             accepted_workers=worker,
#             status='success'
#         )
#
#         # Ikkalasini birlashtirib yuboramiz
#         orders = list(active_orders) + list(completed_orders)
#         serializer = OrderSerializer(orders, many=True)
#
#         return Response(serializer.data)


from django.contrib.gis.geos import Point

class UpdateWorkerLocationAPIView(APIView):
    permission_classes = [IsWorker]

    def post(self, request, *args, **kwargs):
        lon = request.data.get("longitude")
        lat = request.data.get("latitude")

        if not lon or not lat:
            return Response(
                {"detail": "longitude va latitude yuborilishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lon = float(lon)
            lat = float(lat)
        except ValueError:
            return Response(
                {"detail": "longitude va latitude son bo‘lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ PointField yangilash
        request.user.point = Point(lon, lat)
        request.user.save(update_fields=["point"])

        return Response({"detail": "Location updated"}, status=status.HTTP_200_OK)


class WorkerCancelledByClientStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != 'worker':
            return Response({"detail": "Only workers can view this data."}, status=403)

        # Client tomonidan bekor qilingan orderlar
        cancelled_by_client_count = Order.objects.filter(
            accepted_workers=user,
            status='cancel_client'
        ).count()

        # Tugallangan (confirm qilingan) orderlar
        completed_orders_count = Order.objects.filter(
            accepted_workers=user,
            finished_workers=user,
            status='success'
        ).count()

        return Response({
            "cancelled_by_client_orders": cancelled_by_client_count,
            "completed_orders": completed_orders_count
        })
