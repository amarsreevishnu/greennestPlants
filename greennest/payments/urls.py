from django.urls import path
from . import views

urlpatterns = [
    path("cod/<int:order_id>/", views.cod_payment, name="cod_payment"),
    path("wallet/<int:order_id>/", views.wallet_payment, name="wallet_payment"),
    path("razorpay/checkout/", views.razorpay_checkout, name="razorpay_checkout"),
    path("payments/razorpay/callback/", views.razorpay_callback, name="razorpay_callback"),
]
