from django.urls import path
from . import views

urlpatterns = [
    path("", views.wallet_dashboard, name="wallet_dashboard"),
    path("add/", views.add_money, name="add_money"),
]
