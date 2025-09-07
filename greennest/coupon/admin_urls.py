from django.urls import path
from . import admin_views as views


urlpatterns = [
    path("list/", views.coupon_list, name="coupon_list"),
    path("create/", views.coupon_create, name="coupon_create"),
    path("update/<int:pk>/", views.coupon_update, name="coupon_update"),
    path("delete/<int:pk>/", views.coupon_delete, name="coupon_delete"),
]
