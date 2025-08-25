from django.urls import path
from products import user_views as views

# User Product List
urlpatterns = [
    path("", views.user_product_list, name="user_product_list"),  
    path("<int:pk>/", views.user_product_detail, name="user_product_detail"),  
]
