# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard home
    #path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Product management
    path("", views.admin_product_list, name="admin_product_list"),
    path("add/", views.admin_add_product, name="admin_add_product"),
    path("edit/<int:product_id>/", views.admin_edit_product, name="admin_edit_product"),
    path("delete/<int:product_id>/", views.admin_delete_product, name="admin_delete_product"),

    # Category management
    path("categories/", views.admin_category_list, name="admin_category_list"),
    path("categories/add/", views.admin_add_category, name="admin_add_category"),
]
