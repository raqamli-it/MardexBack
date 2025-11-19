import logging
import requests
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from django.db import transaction

from .utils import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserCard, Payment
from .myid_helper import get_myid_access_token
from .serializer import (
    MyIDSessionCreateSerializer,
    MyIDVerifySerializer,
    MyIDSessionStatusSerializer, BindCardInitSerializer, BindCardConfirmSerializer, BindCardDeleteSerializer,
    CreatePaymentSerializer, PreApplySerializer, ConfirmPaymentSerializer, CancelTransactionSerializer
)
from .service import AtmosService


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
    Foydalanuvchini MyID orqali tasdiqlash
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MyIDVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        # MyID tokenni olish
        access_token = get_myid_access_token()
        if not access_token:
            return Response({"detail": "MyID tokenni olishda xatolik"}, status=400)

        # MyID API’dan ma’lumot olish
        url = f"{settings.MYID_BASE_URL}/v1/sdk/data?code={code}"
        headers = {"Authorization": f"Bearer {access_token}"}
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return Response({
                "detail": "MyID ma'lumot olishda xatolik",
                "myid_status": res.status_code,
                "myid_response": res.text,
            }, status=400)

        # MyID'dan kelgan ma’lumot
        response_data = res.json()
        common_data = response_data.get("data", {}).get("profile", {}).get("common_data", {})

        # Asosiy ma’lumotlarni ajratamiz
        pinfl = common_data.get("pinfl")
        first_name = common_data.get("first_name", "")
        last_name = common_data.get("last_name", "")
        passport_number = common_data.get("pass_data") or common_data.get("doc_number", "")
        birth_date = common_data.get("birth_date", "")
        phone = common_data.get("phone") or request.user.phone

        if not pinfl:
            return Response({"detail": "PINFL mavjud emas MyID javobida"}, status=400)

        # Foydalanuvchini olish va yangilash
        user = request.user
        user.pinfl = pinfl
        user.full_name = f"{first_name} {last_name}"
        user.passport_seria = passport_number
        user.birth_date = birth_date
        user.is_verified = True
        user.myid_data = response_data  # ✅ ENG MUHIM QO‘SHIMCHA
        user.save()

        # Tokenlar
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "User verified successfully",
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "pinfl": user.pinfl,
                "passport_seria": user.passport_seria,
                "birth_date": birth_date,
                "phone": user.phone,
                "is_verified": user.is_verified
            },
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            },
            "myid_data": user.myid_data  # endi bazadan olinadi
        }, status=200)


class MyIDClientCredentialsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "client_hash_id": settings.MYID_CLIENT_HASH_ID,
            "client_hash": settings.MYID_CLIENT_HASH,
        })




class MeView(APIView):
    """
    Tasdiqlangan foydalanuvchi ma'lumotlarini olish (MyID verify formatida)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Foydalanuvchi tasdiqlanmagan bo‘lsa
        if not user.is_verified:
            return Response({"detail": "Foydalanuvchi tasdiqlanmagan"}, status=403)

        # Tokenlar yaratish
        refresh = RefreshToken.for_user(user)

        # Tug‘ilgan sana (MyID dagidek bo‘lishi uchun)
        birth_date = None
        if user.myid_data:
            birth_date = (
                user.myid_data.get("data", {})
                .get("profile", {})
                .get("common_data", {})
                .get("birth_date")
            )

        # User ma'lumotlari
        user_data = {
            "id": user.id,
            "full_name": user.full_name,
            "pinfl": user.pinfl,
            "passport_seria": user.passport_seria or "",
            "birth_date": birth_date,
            "phone": user.phone,
            "is_verified": user.is_verified,
        }

        # Yakuniy javob
        return Response(
            {
                "message": "User verified successfully",
                "user": user_data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "myid_data": user.myid_data,  # JSONField dan to‘g‘ridan-to‘g‘ri
            },
            status=200,
        )


class CardBindThrottle(UserRateThrottle):
    rate = "5/min"  # User 1 daqiqada faqat 5 marta init qilishi mumkin


class BindCardInitView(generics.GenericAPIView):
    serializer_class = BindCardInitSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [CardBindThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = serializer.validated_data

        # Prevent duplicate card binding attempts
        if UserCard.objects.filter(user=request.user, status="pending").exists():
            return Response(
                {"error": "Sizda hali tugallanmagan karta tasdiqlash jarayoni mavjud"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Call ATMOS API through safe service layer
        result, code = AtmosService.send_request(
            method="POST",
            url=f"{settings.ATMOS['BASE_URL']}/partner/bind-card/init",
            payload=payload
        )

        # If ATMOS failed
        if code != 200 or result.get("result", {}).get("code") != "OK":
            logger.warning("BindCardInit ERROR: %s", result)
            return Response({"error": result}, status=status.HTTP_400_BAD_REQUEST)

        transaction_id = result.get("transaction_id")
        if not transaction_id:
            logger.error("ATMOS returned no transaction_id: %s", result)
            return Response(
                {"error": "ATMOS noto‘g‘ri javob qaytardi"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Create pending record safely
        UserCard.objects.create(
            user=request.user,
            transaction_id=transaction_id,
            status="pending"
        )

        logger.info(
            "Card bind initiated. user=%s tx_id=%s",
            request.user.id,
            transaction_id
        )

        return Response(
            {
                "transaction_id": transaction_id,
                "phone": result.get("phone"),
                "message": "SMS-kod yuborildi. Tasdiqlash bosqichiga oʻting."
            },
            status=status.HTTP_200_OK
        )

# Bind Card confirm views
class BindCardConfirmView(generics.GenericAPIView):
    serializer_class = BindCardConfirmSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        transaction_id = payload.get("transaction_id")

        # 1) Transaction ID userga tegishli ekanligini tekshirish
        user_card = UserCard.objects.filter(
            user=request.user,
            transaction_id=transaction_id,
            status="pending",
        ).first()

        if not user_card:
            return Response(
                {"error": "Ushbu tranzaksiya sizga tegishli emas yoki muddati o'tgan"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) ATMOS orqali confirm qilish
        result, code = AtmosService.send_request(
            method="POST",
            url=f"{settings.ATMOS['BASE_URL']}/partner/bind-card/confirm",
            payload=payload
        )

        if code != 200 or result.get("result", {}).get("code") != "OK":
            logger.warning("BindCardConfirm API error for user_id=%s, tx=%s", request.user.id, transaction_id)
            return Response({"error": result}, status=status.HTTP_400_BAD_REQUEST)

        card_data = result.get("data") or {}

        # 3) Required fields validation
        for field in ["pan", "card_token", "expiry"]:
            if field not in card_data:
                logger.error("Invalid ATMOS response, missing %s: %s", field, card_data)
                return Response(
                    {"error": "ATMOS noto'g'ri javob qaytardi"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # 4) Duplicate card token check (shifrlangan token bilan)
        encrypted_token = encrypt_value(card_data.get("card_token"))
        if UserCard.objects.filter(
            user=request.user,
            card_token=encrypted_token,
            status="verified"
        ).exists():
            return Response(
                {"error": "Bu karta allaqachon qo‘shilgan"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 5) Save encrypted data safely
        user_card.pan = encrypt_value(card_data.get("pan"))
        user_card.card_token = encrypted_token
        user_card.expiry = encrypt_value(card_data.get("expiry"))
        user_card.card_holder = encrypt_value(card_data.get("card_holder", ""))
        user_card.phone = encrypt_value(card_data.get("phone", ""))
        user_card.status = "verified"
        user_card.save()

        logger.info(
            "Card verified for user_id=%s tx=%s", request.user.id, transaction_id
        )

        # 6) Response uchun masked card tayyorlash
        full_pan = decrypt_value(user_card.pan)
        masked_card = f"{'*' * (len(full_pan) - 4)}{full_pan[-4:]}"  # ****1234

        decrypted = {
            "masked_card": masked_card,
            "expiry": decrypt_value(user_card.expiry),
            "card_holder": decrypt_value(user_card.card_holder),
        }

        return Response(
            {"message": "Karta muvaffaqiyatli tasdiqlandi", **decrypted},
            status=status.HTTP_200_OK,
        )


class CardListPagination(PageNumberPagination): # Pagination list uchun
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

# Card List Get views
class BindCardListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CardListPagination

    def get_queryset(self):
        # Faqat verified va userga tegishli kartalar
        return UserCard.objects.filter(
            user=self.request.user,
            status="verified"
        ).only("card_id", "pan", "expiry", "card_holder", "phone")  # DB-da pan shifrlangan

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        data = []

        for card in page:
            # 1) Panni decrypt qilish va masked_card tayyorlash
            full_pan = decrypt_value(card.pan)
            masked_card = f"{'*' * (len(full_pan) - 4)}{full_pan[-4:]}"  # ****1234

            # 2) Boshqa maydonlarni decrypt qilish
            decrypted_expiry = decrypt_value(card.expiry)
            decrypted_holder = decrypt_value(card.card_holder)
            decrypted_phone = decrypt_value(card.phone)

            data.append({
                "card_id": card.card_id,
                "masked_card": masked_card,
                "expiry": decrypted_expiry,
                "card_holder": decrypted_holder,
                "phone": decrypted_phone,
            })

        return self.get_paginated_response({"cards": data})

# Card delete views
class BindCardDeleteView(generics.GenericAPIView):
    serializer_class = BindCardDeleteSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        # 1) Ownership va status tekshiruvi
        try:
            user_card = UserCard.objects.get(
                user=request.user,
                card_id=payload["card_id"],
                status="verified"
            )
        except UserCard.DoesNotExist:
            return Response(
                {"error": "Card not found or already deleted"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2) ATMOS API chaqiruv (token va pan shifrlangan)
        url = f"{settings.ATMOS['BASE_URL']}/partner/remove-card"
        headers = AtmosAPI.make_headers()
        body = {
            "id": user_card.card_id,
            "token": decrypt_value(user_card.card_token)  # tokenni decrypt qilib yuboramiz
        }

        try:
            response = requests.post(url, json=body, headers=headers, timeout=AtmosAPI.TIMEOUT)
            data = response.json()
        except requests.RequestException:
            logger.exception("BindCardDelete failed for user_id=%s card_id=%s", request.user.id, user_card.card_id)
            return Response({"error": "ATMOS API request failed"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            logger.exception("BindCardDelete response JSON parse failed for user_id=%s card_id=%s", request.user.id, user_card.card_id)
            return Response({"error": "Invalid response from ATMOS API"}, status=status.HTTP_502_BAD_GATEWAY)

        if response.status_code != 200 or data.get("result", {}).get("code") != "OK":
            logger.warning("BindCardDelete API error for user_id=%s card_id=%s: %s", request.user.id, user_card.card_id, data)
            return Response({"error": data}, status=status.HTTP_400_BAD_REQUEST)

        # 3) Atomic update — sensitive ma'lumotlarni tozalash va statusni o'zgartirish
        with transaction.atomic():
            user_card.status = "deleted"
            user_card.card_token = None
            user_card.pan = None
            user_card.expiry = None
            user_card.card_holder = None
            user_card.phone = None
            user_card.save()

        return Response({"message": "Karta muvaffaqiyatli o‘chirildi"}, status=status.HTTP_200_OK)


# Payment create views
class CreatePaymentTransactionView(generics.GenericAPIView):
    serializer_class = CreatePaymentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        # 1) Basic validation
        if payload.get("amount", 0) <= 0:
            return Response({"error": "Amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)

        # 2) ATMOS API call
        try:
            response = requests.post(
                f"{settings.ATMOS['BASE_URL']}/merchant/pay/create",
                json=payload,
                headers=AtmosAPI.make_headers(),
                timeout=AtmosAPI.TIMEOUT
            )
            try:
                data = response.json()
            except ValueError:
                logger.exception("ATMOS CreatePaymentTransaction JSON parse failed")
                return Response({"error": "Invalid response from ATMOS API"}, status=status.HTTP_502_BAD_GATEWAY)

        except requests.RequestException:
            logger.exception("ATMOS CreatePaymentTransaction request failed for user %s", request.user.id)
            return Response({"error": "ATMOS API request failed"}, status=status.HTTP_502_BAD_GATEWAY)

        # 3) ATMOS API response validation
        if response.status_code != 200 or data.get("result", {}).get("code") != "OK":
            logger.warning("ATMOS CreatePaymentTransaction API error for user %s: %s", request.user.id, data)
            return Response({"error": data}, status=status.HTTP_400_BAD_REQUEST)

        transaction_id = data.get("transaction_id")
        if not transaction_id:
            logger.error("ATMOS returned no transaction_id for user %s: %s", request.user.id, data)
            return Response({"error": "ATMOS returned no transaction_id"}, status=status.HTTP_502_BAD_GATEWAY)

        # 4) Save payment with encryption
        with transaction.atomic():
            if Payment.objects.filter(transaction_id=transaction_id).exists():
                return Response({"error": "Transaction already exists"}, status=status.HTTP_409_CONFLICT)

            payment = Payment.objects.create(
                user=request.user,
                transaction_id=transaction_id,
                amount=payload.get("amount"),
                account=encrypt_value(payload.get("account")),
                store_id=encrypt_value(payload.get("store_id")),
                terminal_id=encrypt_value(payload.get("terminal_id")),
                status="draft"
            )

        # 5) Mask sensitive account for response
        full_account = decrypt_value(payment.account)
        masked_account = f"{'*' * (len(full_account) - 4)}{full_account[-4:]}"  # ****1234

        return Response(
            {
                "message": "Tranzaksiya yaratildi",
                "transaction_id": payment.transaction_id,
                "masked_account": masked_account,
                "amount": payment.amount,
            },
            status=status.HTTP_201_CREATED
        )



# PreApply, Confirm, Cancel va GetTransactionInfo
class PreApplyView(generics.GenericAPIView):
    serializer_class = PreApplySerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        # 1) Basic business validation
        if payload.get("amount", 0) <= 0:
            return Response({"error": "Amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)

        # 2) ATMOS API call
        try:
            result, code = AtmosService.pre_apply(payload)
        except requests.RequestException:
            logger.exception("ATMOS PreApply request failed for user %s", request.user.id)
            return Response({"error": "ATMOS API request failed"}, status=status.HTTP_502_BAD_GATEWAY)
        except ValueError:
            logger.exception("ATMOS PreApply JSON parse failed for user %s", request.user.id)
            return Response({"error": "Invalid response from ATMOS API"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            logger.exception("PreApply failed for user %s", request.user.id)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3) ATMOS response validation
        if code != 200 or result.get("result", {}).get("code") != "OK":
            logger.warning("ATMOS PreApply API returned error for user %s: %s", request.user.id, result)
            return Response({"error": result}, status=status.HTTP_400_BAD_REQUEST)

        # 4) Store sensitive info encrypted for audit/logging
        with transaction.atomic():
            transaction_id = result.get("transaction_id")
            # Agar transaction_id mavjud bo'lmasa, log qilamiz
            if not transaction_id:
                logger.error("PreApply returned no transaction_id for user %s: %s", request.user.id, result)
            else:
                # DB ga saqlash, sensitive maydonlarni encrypt qilib
                pre_apply_record = Payment.objects.create(
                    user=request.user,
                    transaction_id=transaction_id,
                    amount=payload.get("amount"),
                    account=encrypt_value(payload.get("account")),  # shifrlash
                    store_id=encrypt_value(payload.get("store_id")),  # shifrlash
                    terminal_id=encrypt_value(payload.get("terminal_id")),  # shifrlash
                    status="pre_applied"
                )
                logger.info("PreApply transaction stored securely for user %s, tx_id=%s", request.user.id,
                            transaction_id)

        # 5) Response masking if needed
        response_data = result.copy()
        if "account" in payload:
            full_account = payload.get("account")
            masked_account = f"{'*' * (len(full_account) - 4)}{full_account[-4:]}"
            response_data["masked_account"] = masked_account
            response_data.pop("account", None)  # Remove raw account

        return Response(response_data, status=status.HTTP_200_OK)


class ConfirmPaymentView(generics.GenericAPIView):
    serializer_class = ConfirmPaymentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        # Business validation
        transaction_id = payload.get("transaction_id")
        if not transaction_id:
            return Response({"error": "transaction_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result, code = AtmosService.confirm_payment(payload)
        except requests.RequestException as e:
            logger.exception("ATMOS ConfirmPayment request failed for user %s, transaction %s", request.user.id, transaction_id)
            return Response({"error": "ATMOS API request failed"}, status=status.HTTP_502_BAD_GATEWAY)
        except ValueError as e:  # JSON parse error
            logger.exception("ATMOS ConfirmPayment JSON parse failed for user %s, transaction %s", request.user.id, transaction_id)
            return Response({"error": "Invalid response from ATMOS API"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            logger.exception("ConfirmPayment failed for user %s, transaction %s", request.user.id, transaction_id)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if code != 200 or result.get("result", {}).get("code") != "OK":
            logger.warning("ATMOS ConfirmPayment API returned error for user %s, transaction %s: %s", request.user.id, transaction_id, result)
            return Response({"error": result}, status=status.HTTP_400_BAD_REQUEST)

        # Optional: save confirmed transaction to DB
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(transaction_id=transaction_id, user=request.user)

            # Status update
            payment.status = "confirmed"

            # Agar ATMOS response’da account/store_id/terminal_id kelgan bo‘lsa, shifrlab saqlash
            if "account" in payload:
                payment.account = encrypt_value(payload.get("account"))
            if "store_id" in payload:
                payment.store_id = encrypt_value(payload.get("store_id"))
            if "terminal_id" in payload:
                payment.terminal_id = encrypt_value(payload.get("terminal_id"))

            payment.save()
            logger.info("Payment confirmed and stored securely for user %s, tx=%s", request.user.id, transaction_id)

        return Response(result, status=status.HTTP_200_OK)


class GetTransactionInfoView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        # Business validation: check if transaction exists
        if not Payment.objects.filter(transaction_id=order_id, user=request.user).exists():
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            result, code = AtmosService.check_status(order_id)
        except requests.RequestException as e:
            logger.exception("ATMOS check_status request failed for user %s, transaction %s", request.user.id, order_id)
            return Response({"error": "ATMOS API request failed"}, status=status.HTTP_502_BAD_GATEWAY)
        except ValueError as e:  # JSON parse error
            logger.exception("ATMOS check_status JSON parse failed for user %s, transaction %s", request.user.id, order_id)
            return Response({"error": "Invalid response from ATMOS API"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            logger.exception("GetTransactionInfo failed for user %s, transaction %s", request.user.id, order_id)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if code != 200:
            logger.warning("ATMOS check_status returned HTTP %s for user %s, transaction %s", code, request.user.id, order_id)
            return Response({"error": "ATMOS API returned error", "details": result}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class CancelTransactionView(generics.GenericAPIView):
    serializer_class = CancelTransactionSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        # Business validation: check if transaction exists for this user
        transaction_id = payload.get("transaction_id")
        if not Payment.objects.filter(transaction_id=transaction_id, user=request.user).exists():
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            result, code = AtmosService.cancel_transaction(payload)
        except requests.RequestException as e:
            logger.exception(
                "ATMOS cancel_transaction request failed for user %s, transaction %s",
                request.user.id, transaction_id
            )
            return Response({"error": "ATMOS API request failed"}, status=status.HTTP_502_BAD_GATEWAY)
        except ValueError as e:
            logger.exception(
                "ATMOS cancel_transaction JSON parse failed for user %s, transaction %s",
                request.user.id, transaction_id
            )
            return Response({"error": "Invalid response from ATMOS API"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            logger.exception(
                "CancelTransaction failed for user %s, transaction %s",
                request.user.id, transaction_id
            )
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if code != 200:
            logger.warning(
                "ATMOS cancel_transaction returned HTTP %s for user %s, transaction %s",
                code, request.user.id, transaction_id
            )
            return Response({"error": "ATMOS API returned error", "details": result}, status=status.HTTP_400_BAD_REQUEST)

        # Optionally update Payment model status
        Payment.objects.filter(transaction_id=transaction_id, user=request.user).update(status="cancelled")

        return Response(result, status=status.HTTP_200_OK)
