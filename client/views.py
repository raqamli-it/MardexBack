from job.views import get_filtered_workers
from users.models import AbstractUser
from worker.models import WorkerImage
from worker.serializers import WorkerSerializer
from .models import Order, ClientNews, ClientTarif, TarifHaridi
from .serializer import (
    OrderSerializer, ClientNewsSerializer, ClientTarifSerializer,
    TarifHaridiSerializer, ClientPhoneUpdateSerializer
)
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializer import (ClientRegistrationSerializer, ClientLoginSerializer, ClientPasswordChangeSerializer,
                         ClientDetailSerializer)

from django.contrib.auth import get_user_model
from job.models import Job, CategoryJob
from job.serializer import CategoryJobSerializer, JobSerializer

User = get_user_model()


### Order Views


class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Order yaratish va filterlangan workerlarni qaytarish"""
        self.order = serializer.save(client=self.request.user)
        self.eligible_workers = get_filtered_workers(self.order)

    def create(self, request, *args, **kwargs):
        """Overriding to return custom response"""
        response = super().create(request, *args, **kwargs)

        workers_data = [
            {
                "id": w.id,
                "full_name": w.full_name,
                "avatar": w.avatar.url if w.avatar else None,
                "job_id": list(w.job_id.values_list("id", flat=True)),
                "description": w.description,
                "reyting": w.reyting,
                "images": [
                    {"id": img.id, "image": img.image.url if img.image else None}
                    for img in WorkerImage.objects.filter(user=w)  # WorkerImage dan olish
                ]
            }
            for w in self.eligible_workers
        ]

        return Response({
            "detail": "Order muvaffaqiyatli yaratildi!",
            "order": OrderSerializer(self.order).data,
            "eligible_workers": workers_data
        })


class JobListByCategoryView(APIView):
    def get(self, request, pk):
        category_job = get_object_or_404(CategoryJob, id=pk)
        jobs = Job.objects.filter(category_job=category_job)
        category_serializer = CategoryJobSerializer(category_job, context={'request': request})
        jobs_serializer = JobSerializer(jobs, many=True, context={'request': request})

        result = category_serializer.data
        result['jobs'] = jobs_serializer.data

        return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
def categoryjob_list(request):
    category_jobs = CategoryJob.objects.all()
    serializer = CategoryJobSerializer(category_jobs, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# Client Views
class ClientRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = ClientRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()

        # Assign default tariff
        self.assign_default_tarif(client)

        refresh = RefreshToken.for_user(client)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

    def assign_default_tarif(self, user):
        default_tarif = ClientTarif.objects.filter(price=0).first()
        if default_tarif:
            TarifHaridi.objects.get_or_create(user=user, tarif_id=default_tarif)


class ClientLoginView(generics.GenericAPIView):
    serializer_class = ClientLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.validated_data

        if client.role != 'client':
            return Response({"error": "Only clients can login here."}, status=status.HTTP_403_FORBIDDEN)

        tarif_info = self.get_or_assign_tarif(client)

        refresh = RefreshToken.for_user(client)
        refresh['role'] = client.role

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "client": ClientRegistrationSerializer(client).data,
            "tarif": tarif_info,
        }, status=status.HTTP_200_OK)

    def get_or_assign_tarif(self, user):
        """
        Foydalanuvchining aktiv tarifini olish yoki unga 0 so‘mlik tarifni ulash.
        """
        # Foydalanuvchining aktiv tarifini tekshirish
        tarif_haridi = TarifHaridi.objects.filter(user=user, status=True).first()
        if tarif_haridi:
            tarif = tarif_haridi.tarif_id
        else:
            # 0 so‘mlik tarifni olish
            default_tarif = ClientTarif.objects.filter(price=0).first()
            if not default_tarif:
                return None  # Agar 0 so‘mlik tarif bo‘lmasa, `None` qaytaramiz

            # 0 so‘mlik tarifni foydalanuvchiga bog‘lash
            tarif_haridi, created = TarifHaridi.objects.get_or_create(
                user=user,
                tarif_id=default_tarif,
                defaults={"status": True}
            )

            # Agar yozuv avval mavjud bo‘lsa, statusni yangilaymiz
            if not created:
                tarif_haridi.status = True
                tarif_haridi.save()

            tarif = tarif_haridi.tarif_id

        return {
            "id": tarif.id,
            "name": tarif.name,
            "price": tarif.price,
            "top_limit": tarif.top_limit,
            "call_limit": tarif.call_limit,
        }


class IsClient(BasePermission):
    def has_permission(self, request, view):
        # Tokendagi rolni tekshirish
        token = request.auth
        if token:
            return token.get('role') == 'client'
        return False


class ClientPasswordChangeView(generics.GenericAPIView):
    serializer_class = ClientPasswordChangeSerializer
    permission_classes = [IsAuthenticated, IsClient]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Password updated successfully."})

    def perform_update(self, serializer):
        serializer.save()


class ClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        client = request.user
        serializer = ClientDetailSerializer(client, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        client = request.user
        serializer = ClientDetailSerializer(client, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = ClientRegistrationSerializer


### News Views

@api_view(['GET'])
def newsclient_list(request):
    news = ClientNews.objects.all()
    serializer = ClientNewsSerializer(news, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


class ClientNewsDetailView(APIView):
    def get(self, request, pk):
        client_news = get_object_or_404(ClientNews, pk=pk)
        serializer = ClientNewsSerializer(client_news, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


### Tariff Views

class TarifHaridiCreateView(generics.CreateAPIView):
    queryset = TarifHaridi.objects.all()
    serializer_class = TarifHaridiSerializer


@api_view(['GET'])
def clienttarif_list(request):
    if not request.user.is_authenticated:
        return Response({"detail": "Authentication credentials were not provided."},
                        status=status.HTTP_401_UNAUTHORIZED)

    tarif = TarifHaridi.objects.filter(user=request.user)
    serializer = TarifHaridiSerializer(tarif, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def tarif_list(request):
    clienttarif = ClientTarif.objects.all()
    serializer = ClientTarifSerializer(clienttarif, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


class ClientPhoneUpdateView(generics.GenericAPIView):
    serializer_class = ClientPhoneUpdateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Phone number updated successfully."}, status=status.HTTP_200_OK)


class ClientProfileView(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            serializer = ClientDetailSerializer(request.user)
            return Response(serializer.data)
        else:
            return Response({"detail": "Foydalanuvchi tizimga kirmagan"}, status=401)


class FilteredWorkerListView(generics.ListAPIView):
    serializer_class = WorkerSerializer

    def get_queryset(self):
        order_id = self.kwargs.get("order_id")
        try:
            order = Order.objects.get(id=order_id)
            return get_filtered_workers(order)
        except Order.DoesNotExist:
            return AbstractUser.objects.none()
