from django.urls import path
from . import admin_views as views

urlpatterns=[
    
    path("", views.admin_wallet_dashboard, name="admin_wallet"),
    path('admin/wallet/transaction/<int:transaction_id>/', views.admin_transaction_detail, name='admin_transaction_detail'),
]