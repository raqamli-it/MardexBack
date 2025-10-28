from django.urls import path

from users.views import MyIDCreateSessionView, MyIDSessionStatusView, MyIDVerifyView, MyIDGetTokenView

urlpatterns = [
    path("get-token/", MyIDGetTokenView.as_view(), name="myid-get-token"),
    path('create-session/', MyIDCreateSessionView.as_view(), name='myid-create-session'),
    path('session-status/', MyIDSessionStatusView.as_view(), name='myid-session-status'),
    path('verify/', MyIDVerifyView.as_view(), name='myid-verify'),

]
