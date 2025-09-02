from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test, login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from functools import wraps

from users.views import User
from orders.models import Order

User = get_user_model()

# Only superusers can access
def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return redirect("/greennest_admin/")  
    return _wrapped_view


@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')  
            else:
                messages.error(request, 'You are not authorized as admin.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'admin_login.html')



@admin_required
def admin_logout(request):
    logout(request)
    request.session.flush() 
    return redirect('admin_login')


@admin_required
@never_cache
def admin_dashboard(request):
    order_count = Order.objects.count()
    user_count = User.objects.filter(is_superuser=False).count()
    orders = Order.objects.select_related('user').all().order_by('-created_at')

    context = {
        'order_count': order_count,
        'user_count': user_count,
        'orders': orders[:5],
    }
    return render(request, 'admin_dashboard.html', context)



@admin_required
@never_cache
def user_list(request):
    query = request.GET.get('q', '')

    
    users = User.objects.filter(is_superuser=False)

    # Search by first_name, last_name, or email
    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

    users = users.order_by('-id')

    # Pagination: 10 users per page
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_user_list.html', {
        'users': page_obj,   
        'query': query
    })

@admin_required
@never_cache
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        user.is_active = not user.is_active
        user.save()
        action = "unblocked" if user.is_active else "blocked"
        # messages.success(request, f"User {user.username} has been {action}.")

    return redirect('admin_user_list')