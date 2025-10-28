from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import AbstractUser
from .myid_service import start_verification, get_verification_result


class StartMyIDVerification(APIView):
    """
    Android foydalanuvchidan ma'lumot oladi va MyID verifikatsiya jarayonini boshlaydi.
    """
    def post(self, request):
        try:
            data = request.data
            response = start_verification(data)
            return Response({
                "verification_id": response.get("verification_id"),
                "verification_url": response.get("verification_url")
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MyIDCallbackView(APIView):
    """
    MyID foydalanuvchini tekshirgach shu URL'ga qaytadi.
    Django shu joyda foydalanuvchini verified qiladi.
    """
    def get(self, request):
        verification_id = request.query_params.get("verification_id")
        status_param = request.query_params.get("status")

        if not verification_id or status_param != "success":
            return Response({"error": "Verification failed"}, status=status.HTTP_400_BAD_REQUEST)

        result = get_verification_result(verification_id)

        if result.get("status") == "VERIFIED":
            jshshir = result.get("pinfl")
            full_name = result.get("full_name")
            passport_seria = result.get("document_series")
            passport_number = result.get("document_number")

            user, created = AbstractUser.objects.get_or_create(
                passport_seria=passport_seria,
                defaults={
                    "full_name": full_name,
                    "jshshir": jshshir,
                    "is_active": True
                }
            )

            # Tasdiqlangan deb belgilaymiz
            user.is_verified = True
            user.save()

            return Response({
                "success": True,
                "verified": True,
                "message": "User successfully verified",
                "user_id": user.id,
                "full_name": user.full_name
            })
        else:
            return Response({
                "success": False,
                "message": "Verification not completed"
            }, status=status.HTTP_400_BAD_REQUEST)
