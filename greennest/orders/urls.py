from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout_address, name='checkout_address'),
    path('checkout/payment/', views.checkout_payment, name='checkout_payment'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path("list/", views.order_list, name="order_list"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),

    path("<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("item/<int:item_id>/cancel/", views.cancel_order_item, name="cancel_order_item"),
    
    path('request-return/<int:order_id>/item/<int:item_id>/', views.request_return_item, name='request_return_item'),
    path('invoice/<int:order_id>/download/', views.download_invoice, name='download_invoice'),
]
