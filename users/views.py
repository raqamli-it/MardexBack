import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings

from .myid_helper import get_myid_access_token
from .permission import IsMyIDTokenValid
from .serializer import (
    MyIDSessionCreateSerializer,
    MyIDVerifySerializer,
    MyIDSessionStatusSerializer
)

# Access tokenni olish uchun (agar alohida test qilmoqchi bo‘lsangiz)
class MyIDGetTokenView(APIView):
    def get(self, request):
        try:
            token = get_myid_access_token()
            return Response({"access_token": token}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Session yaratish (foydalanuvchi ma’lumotlari asosida)
class MyIDCreateSessionView(APIView):
    """
     Sessiya yaratish — MyID orqali shaxsni tasdiqlashni boshlash
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MyIDSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        access_token = get_myid_access_token()

        url = f"{settings.MYID_BASE_URL}/v2/sdk/sessions"
        headers = {"Authorization": f"Bearer {access_token}"}
        body = {
            "phone_number": data.get("phone_number"),
            "birth_date": str(data.get("birth_date")) if data.get("birth_date") else None,
            "is_resident": data.get("is_resident"),
            "pass_data": data.get("pass_data"),
            "pinfl": data.get("pinfl"),
        }

        res = requests.post(url, json=body, headers=headers)
        if res.status_code != 200:
            return Response({
                "detail": "Session yaratishda xatolik",
                "error": res.text
            }, status=res.status_code)

        session_id = res.json().get("session_id")

        return Response({
            "message": "Session created successfully",
            "session_id": session_id,
            "expires_in_seconds": 600
        }, status=200)


#  Session statusni tekshirish (session_id orqali)
class MyIDSessionStatusView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MyIDSessionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]

        access_token = get_myid_access_token()
        url = f"{settings.MYID_BASE_URL}/v1/sdk/sessions/{session_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        res = requests.get(url, headers=headers)

        if res.status_code != 200:
            return Response({
                "detail": "Session statusni olishda xatolik",
                "myid_status_code": res.status_code,
                "myid_response": res.text
            }, status=res.status_code)

        return Response({
            "status": res.json().get("status"),
            "data": res.json()
        }, status=200)


class MyIDVerifyView(APIView):
    """
    Foydalanuvchini MyID code orqali tasdiqlash
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MyIDVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        access_token = get_myid_access_token()
        url = f"{settings.MYID_BASE_URL}/v1/sdk/data?code={code}"
        headers = {"Authorization": f"Bearer {access_token}"}

        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return Response({
                "detail": "Ma'lumot olishda xatolik",
                "myid_status": res.status_code,
                "myid_response": res.text,
                "requested_url": url
            }, status=res.status_code)

        data = res.json()

        # MyID'dan kelgan ma'lumotlar
        pinfl = data.get("pinfl")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        passport_number = data.get("passport_number", "")
        birth_date = data.get("birth_date", "")

        # Foydalanuvchini yaratish yoki yangilash
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user, created = User.objects.get_or_create(
            pinfl=pinfl,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "passport_number": passport_number,
                "birth_date": birth_date
            }
        )

        if not created:
            # mavjud foydalanuvchini yangilash
            user.first_name = first_name
            user.last_name = last_name
            user.passport_number = passport_number
            user.birth_date = birth_date
            user.save()

        # Foydalanuvchi uchun JWT token yaratish
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "User verified successfully",
            "myid_data": data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }
        }, status=200)


class MyIDClientCredentialsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "client_hash_id": settings.MYID_CLIENT_HASH_ID,
            "client_hash": settings.MYID_CLIENT_HASH,
        })




# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
#
# from users.myid_service import create_session, get_user_data
#
#
# class MyIDSessionView(APIView):
#     def post(self, request):
#         pass_data = request.data.get("pass_data")
#         birth_date = request.data.get("birth_date")
#         is_resident = request.data.get("is_resident", True)
#         try:
#             session_id = create_session(pass_data, birth_date, is_resident)
#             return Response({"session_id": session_id}, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
#
#
# class MyIDVerifyView(APIView):
#     def post(self, request):
#         code = request.data.get("code")
#         try:
#             data = get_user_data(code)
#             return Response(data, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
