
from django.urls import path
from . import views

urlpatterns = [
    path('login/',views.user_login, name='user_login'),
    path('signup/',views.user_signup,name='user_signup'),
    path ('verify_otp/', views.verify_otp, name='verify_otp'),
]
