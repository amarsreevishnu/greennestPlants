from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout_address, name='checkout_address'),
    path('checkout/payment/', views.checkout_payment, name='checkout_payment'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path("list/", views.order_list, name="order_list"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
]
