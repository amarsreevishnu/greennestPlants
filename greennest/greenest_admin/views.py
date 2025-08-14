from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from users.views import User

# Create your views here.
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('admin_user_list')  # redirect to user management page
            else:
                messages.error(request, 'You are not authorized as admin.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'admin_login.html')

# check if user is admin
def is_admin(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(is_admin)
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

def admin_dashboard(request):
    # Render the admin dashboard template
    return render(request, 'admin_dashboard.html')


User = get_user_model()

# Only superusers can access
def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser, login_url='admin_login')(view_func)


@superuser_required
def user_list(request):
    query = request.GET.get('q', '')

    # Filter users (exclude superusers)
    users = User.objects.filter(is_superuser=False)

    # Search by first_name, last_name, or email
    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

    # Order by latest first
    users = users.order_by('-id')

    # Pagination: 10 users per page
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_user_list.html', {
        'users': page_obj,   # send paginated users
        'query': query
    })
# Toggle user status
@superuser_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        user.is_active = not user.is_active
        user.save()
        action = "unblocked" if user.is_active else "blocked"
        messages.success(request, f"User {user.username} has been {action}.")

    return redirect('admin_user_list')