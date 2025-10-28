from django.urls import path

from users.views import MyIDCallbackView, StartMyIDVerification

# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
#
# from users.views import ProtectedView, RegisterAPIView, CustomTokenObtainPairView

urlpatterns = [
    path("myid/start-verification/", StartMyIDVerification.as_view()),
    path("myid/callback/", MyIDCallbackView.as_view()),

    # path('api/register/', RegisterAPIView.as_view(), name='register'),  # Registratsiya
    # path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),  # Login
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Token yangilash
    # path('protected/', ProtectedView.as_view(), name='protected_view'),  # Himoyalangan

]
