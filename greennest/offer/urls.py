from django.urls import path
from . import views

urlpatterns = [
    # Product Offers
    path('product-offers/', views.product_offer_list, name='product_offer'),
    path('product-offers/add/', views.product_offer_create, name='product_offer_create'),
    path('product-offers/edit/<int:pk>/', views.product_offer_edit, name='product_offer_edit'),
    path('product-offers/delete/<int:pk>/', views.product_offer_delete, name='product_offer_delete'),
    

    # Category Offers
    path('category-offers/', views.category_offer_list, name='category_offer'),
    path('category-offers/add/', views.category_offer_create, name='category_offer_create'),
    path('category-offers/edit/<int:pk>/', views.category_offer_edit, name='category_offer_edit'),
    path('category-offers/delete/<int:pk>/', views.category_offer_delete, name='category_offer_delete'),
    path('category-offers/toggle/<int:offer_id>/', views.toggle_category_offer, name='toggle_category_offer'),
]
