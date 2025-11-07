import requests
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MyIDVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        role = request.data.get("role", "client")

        # MyID token olish
        access_token = get_myid_access_token()
        if not access_token:
            return Response({"detail": "MyID tokenni olishda xatolik"}, status=400)

        # Ma’lumot olish
        url = f"{settings.MYID_BASE_URL}/v1/sdk/data?code={code}"
        headers = {"Authorization": f"Bearer {access_token}"}
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return Response({
                "detail": "MyID ma'lumot olishda xatolik",
                "myid_status": res.status_code,
                "myid_response": res.text,
            }, status=400)

        response_data = res.json()
        common_data = response_data.get("data", {}).get("profile", {}).get("common_data", {})

        pinfl = common_data.get("pinfl")
        first_name = common_data.get("first_name", "")
        last_name = common_data.get("last_name", "")
        passport_number = common_data.get("pass_data") or common_data.get("doc_number", "")
        birth_date = common_data.get("birth_date", "")
        phone = common_data.get("phone") or f"unknown_{pinfl}"

        if not pinfl:
            return Response({"detail": "PINFL mavjud emas MyID javobida"}, status=400)

        User = get_user_model()

        # 🧠 1️⃣ Avval request.user dan tekshiramiz (agar foydalanuvchi allaqachon login bo‘lgan bo‘lsa)
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            user.pinfl = pinfl
            user.full_name = f"{first_name} {last_name}"
            user.passport_seria = passport_number
            user.is_verified = True
            user.role = role
            user.save()
            created = False

        else:
            # 🧠 2️⃣ Aks holda phone yoki pinfl orqali tekshiramiz
            existing_user = User.objects.filter(phone=phone).first() or User.objects.filter(pinfl=pinfl).first()
            if existing_user:
                existing_user.pinfl = pinfl
                existing_user.full_name = f"{first_name} {last_name}"
                existing_user.passport_seria = passport_number
                existing_user.is_verified = True
                existing_user.role = role
                existing_user.save()
                user = existing_user
                created = False
            else:
                # 🧠 3️⃣ Hech biri topilmasa yangi yaratamiz
                user, created = User.objects.get_or_create(
                    pinfl=pinfl,
                    defaults={
                        "full_name": f"{first_name} {last_name}",
                        "passport_seria": passport_number,
                        "phone": phone,
                        "role": role,
                        "is_verified": True,
                    },
                )

        # Token yaratish
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Foydalanuvchi tasdiqlandi",
            "created": created,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "pinfl": user.pinfl,
                "passport_seria": user.passport_seria,
                "birth_date": birth_date,
                "phone": user.phone,
                "role": user.role,
                "is_verified": user.is_verified,
            },
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "myid_data": response_data
        }, status=200)


# class MyIDVerifyView(APIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request):
#         serializer = MyIDVerifySerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         code = serializer.validated_data["code"]
#
#         access_token = get_myid_access_token()
#         if not access_token:
#             return Response({"detail": "MyID tokenni olishda xatolik"}, status=400)
#
#         url = f"{settings.MYID_BASE_URL}/v1/sdk/data?code={code}"
#         headers = {"Authorization": f"Bearer {access_token}"}
#         res = requests.get(url, headers=headers)
#
#         if res.status_code != 200:
#             return Response({
#                 "detail": "Ma'lumot olishda xatolik",
#                 "myid_status": res.status_code,
#                 "myid_response": res.text,
#             }, status=400)
#
#         response_data = res.json()
#         common_data = response_data.get("data", {}).get("profile", {}).get("common_data", {})
#
#         pinfl = common_data.get("pinfl")
#         first_name = common_data.get("first_name", "")
#         last_name = common_data.get("last_name", "")
#         passport_number = common_data.get("pass_data") or common_data.get("doc_number", "")
#         birth_date = common_data.get("birth_date", "")
#         phone = common_data.get("phone") or f"unknown_{pinfl}"
#         role = "client"
#
#         if not pinfl:
#             return Response({"detail": "PINFL mavjud emas MyID javobida"}, status=400)
#
#         User = get_user_model()
#         user, created = User.objects.get_or_create(
#             pinfl=pinfl,
#             defaults={
#                 "full_name": f"{first_name} {last_name}",
#                 "passport_seria": passport_number,
#                 "phone": phone,
#                 "role": role,
#                 "is_verified": True,  # ✅
#             }
#         )
#
#         # Har doim yangilab qo‘yamiz
#         user.is_verified = True
#         user.full_name = f"{first_name} {last_name}"
#         user.passport_seria = passport_number
#         user.save()
#
#         refresh = RefreshToken.for_user(user)
#
#         return Response({
#             "message": "User verified successfully",
#             "created": created,
#             "user": {
#                 "id": user.id,
#                 "full_name": user.full_name,
#                 "pinfl": user.pinfl,
#                 "passport_seria": user.passport_seria,
#                 "birth_date": birth_date,
#                 "is_verified": user.is_verified,
#             },
#             "tokens": {
#                 "refresh": str(refresh),
#                 "access": str(refresh.access_token),
#             },
#             "myid_data": response_data
#         }, status=200)


class MyIDClientCredentialsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "client_hash_id": settings.MYID_CLIENT_HASH_ID,
            "client_hash": settings.MYID_CLIENT_HASH,
        })




class MeView(APIView):
    """
    Tasdiqlangan foydalanuvchi ma'lumotlarini olish
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not user.is_verified:
            return Response({"detail": "Foydalanuvchi tasdiqlanmagan"}, status=403)

        return Response({
            "id": user.id,
            "full_name": user.full_name,
            "pinfl": user.pinfl,
            "passport_seria": user.passport_seria,
            "birth_date": user.birth_date,
            "is_verified": user.is_verified
        }, status=200)
