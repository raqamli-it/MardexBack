from django.urls import path

from users.views import MyIDCreateSessionView, MyIDSessionStatusView, MyIDVerifyView, MyIDGetTokenView, \
    MyIDClientCredentialsView, MeView, BindCardInitView, BindCardConfirmView, BindCardListView, BindCardDeleteView, \
    CreatePaymentTransactionView, PreApplyView, TestAtmosTokenView, ConfirmPaymentView, GetTransactionInfoView, \
    CancelTransactionView

urlpatterns = [
    path("get-token/", MyIDGetTokenView.as_view(), name="myid-get-token"),
    path('create-session/', MyIDCreateSessionView.as_view(), name='myid-create-session'),
    path('session-status/', MyIDSessionStatusView.as_view(), name='myid-session-status'),
    path('verify/', MyIDVerifyView.as_view(), name='myid-verify'),
    path("myid-credentials/", MyIDClientCredentialsView.as_view(), name="myid-credentials"),
    path("my-data-view/", MeView.as_view(), name="my-data-view"),

    path("bind-card/init/", BindCardInitView.as_view(), name="bind_card_init"), # Card add url
    path("card/bind/confirm/", BindCardConfirmView.as_view()), # Card confirm url

    # User bog‘langan card get url
    path("bind-card/list/", BindCardListView.as_view(), name="bind_card_list"),

    #  Card delete url
    path("bind-card/delete/", BindCardDeleteView.as_view(), name="bind_card_delete"),

    # Tranzaksiya create url
    path("payment/create/", CreatePaymentTransactionView.as_view(), name="create_payment"),

    # Transactionni oldindan tasdiqlash url (pre-apply)
    path("payment/pre-confirm/", PreApplyView.as_view(), name="payment_pre_apply"),

    # payment confirm url
    path("payment/confirm/", ConfirmPaymentView.as_view(), name="payment_confirm"),

    # Bu endpoint orqali ma’lum bir tranzaksiya haqida ma’lumot olish mumkin
    path("payment/<int:order_id>/info/", GetTransactionInfoView.as_view(), name="payment_info"),

    # Bu endpoint orqali mavjud tranzaksiyani bekor qilish mumkin
    path("payment/cancel/", CancelTransactionView.as_view(), name="payment_cancel"),

    # GET ATMOS token
    path("atmos-test-token/", TestAtmosTokenView.as_view(), name="atmos_test_token"),

]
