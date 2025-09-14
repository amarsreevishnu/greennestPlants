from django.urls import path
from . import views

urlpatterns = [
    path("", views.wallet_dashboard, name="wallet_dashboard"), 
    path("create_wallet_order/",views.create_wallet_order,name="create_wallet_order"),
    path("verify_wallet_payment/",views.verify_wallet_payment, name="verify_wallet_payment")
]
