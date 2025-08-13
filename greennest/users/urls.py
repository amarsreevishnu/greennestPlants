
from django.urls import path
from . import views

urlpatterns = [
    path('login/',views.user_login, name='user_login'),
    path('signup/',views.user_signup,name='user_signup'),
    path ('verify_otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp-ajax/', views.resend_otp_ajax, name='resend_otp_ajax'),
    path('logout/', views.user_logout, name='logout'),
    path('user_home/', views.user_home, name='user_home'),
    path('forget_password/', views.forget_password, name='forget_password'),
    path ('verify_reset_otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset_password/', views.reset_password, name='reset_password'),
]
