from django.urls import path
from . import views

urlpatterns = [
    path('', views.wishlist_view, name='wishlist_view'),
    path('toggle/<int:variant_id>/', views.toggle_wishlist, name='toggle_wishlist'),
     path('remove/<int:variant_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
]