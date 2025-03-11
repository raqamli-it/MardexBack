from django.urls import path

from .sent_order import SendOrderToSelectedWorkersView
from .views import ClientDetailView, ClientNewsDetailView, OrderCreateView, FilteredWorkerListView

from .views import (
    OrderListView,
    OrderDetailView,
    newsclient_list,
    TarifHaridiCreateView,
    clienttarif_list,
    tarif_list,
    ClientListView,
    ClientPhoneUpdateView,
)
from django.conf import settings
from django.conf.urls.static import static

from .views import ClientRegistrationView, ClientLoginView, ClientPasswordChangeView, ClientProfileView


urlpatterns = [
    path('orderscreate/', OrderCreateView.as_view(), name='order-create'),
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('clientnews/', newsclient_list),
    path('register/', ClientRegistrationView.as_view(), name='client-register'),
    path('login/', ClientLoginView.as_view(), name='client-login'),
    path('password-change/', ClientPasswordChangeView.as_view(), name='client-password-change'),

    path('api/client/update-phone/', ClientPhoneUpdateView.as_view(), name='client-update-phone'),
    path('profiles/', ClientDetailView.as_view(), name='client-detail'),

    path('tarifharid/', TarifHaridiCreateView.as_view(), name='tarif-harid'),
    path('clientnews/', newsclient_list),
    path('clientnews/<int:pk>/', ClientNewsDetailView.as_view(), name='newsclient-detail'),
    path('clienttariflist/', clienttarif_list),
    path('tarif/', tarif_list),
    path('clients/', ClientListView.as_view(), name='client-list'),

    path('filtered-workers/<int:order_id>/', FilteredWorkerListView.as_view(), name='filtered-workers'),
    path('sent_order/', SendOrderToSelectedWorkersView.as_view(), name='sent-order'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    path('profile/', ClientProfileView.as_view(), name='client-profile'),


