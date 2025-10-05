
from django.urls import path
from . import views

urlpatterns = [
    path('',views.admin_login, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('users/', views.user_list, name='admin_user_list'),
    path('users/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('add-banner/', views.add_banner, name='add_banner'),
    path('edit-banner/<int:banner_id>/', views.edit_banner, name='edit_banner'),
    path('delete-banner/<int:banner_id>/', views.delete_banner, name='delete_banner'),
    

]