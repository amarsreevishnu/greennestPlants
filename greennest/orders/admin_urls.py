from django.urls import path
from . import admin_views as views

urlpatterns = [
    path('', views.admin_order_list, name='admin_order_list'),
    path('<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),

    path('sales-report/', views.sales_report, name='sales_report'),
    path("sales-report/pdf/", views.download_sales_report_pdf, name="download_sales_report_pdf"),
]
