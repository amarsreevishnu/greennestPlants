from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages

from .models import Order

@login_required(login_url='admin_login')
@never_cache
def admin_order_list(request):
    orders = Order.objects.select_related('user').all().order_by('-created_at')

    # --- Search ---
    search_query = request.GET.get('search', '').strip()
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    # --- Filter by status ---
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    # --- Sort ---
    sort_by = request.GET.get('sort', 'created_at')
    if sort_by in ['created_at', 'final_amount', 'status']:
        orders = orders.order_by('-' + sort_by)

    # --- Pagination ---
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
    }
    return render(request, 'admin/order_list.html', context)



@login_required(login_url='admin_login')
@never_cache
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Order.STATUS_CHOICES).keys():
            order.status = new_status
            order.save()
            messages.success(request, f"Order status updated to {order.get_status_display()}")
        else:
            messages.error(request, "Invalid status selected.")

        return redirect("admin_order_detail", order_id=order.id)

    return render(request, 'admin/order_detail.html', {'order': order, 'order_items': order_items})

