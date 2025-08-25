# products/urls.py
from django.urls import path
from products import admin_views as views

urlpatterns = [
    

    # Admin Product management
    path("", views.admin_product_list, name="admin_product_list"),
    path("add/", views.admin_add_product, name="admin_add_product"),
    path("edit/<int:product_id>/", views.admin_edit_product, name="admin_edit_product"),
    path("delete/<int:product_id>/", views.admin_delete_product, name="admin_delete_product"),

    # Admin Category management
    path("categories/", views.manage_categories, name="manage_categories"),
    path("categories/<int:pk>/", views.manage_categories, name="manage_categories"),  # Edit
    path("categories/toggle/<int:pk>/", views.toggle_category_status, name="toggle_category_status"),


    
]
