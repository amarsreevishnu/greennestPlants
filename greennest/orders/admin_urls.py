from django.urls import path
from . import admin_views as views

urlpatterns = [
    path('', views.admin_order_list, name='admin_order_list'),
    path('<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),

    
]
