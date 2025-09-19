from django.urls import path
from . import admin_views as views

urlpatterns=[
    path("",views.wallet_list,name="admin_wallet_list"),
    path("wallet-details/<int:transaction_id>/",views.wallet_detials,name="admin_wallet_details")
]