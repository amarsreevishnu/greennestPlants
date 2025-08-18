
from django.urls import path
from . import views

urlpatterns = [
    path('',views.admin_login, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('users/', views.user_list, name='admin_user_list'),
    path('users/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),

]