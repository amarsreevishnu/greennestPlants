from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db.models import Q, Exists, OuterRef
from django.contrib import messages
from django.utils import timezone
from orders.models import Order, OrderItem

from django.db.models import Q, Exists, OuterRef
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from orders.models import Order, OrderItem

@login_required(login_url='admin_login')
@never_cache
def admin_order_list(request):
    orders = Order.objects.select_related('user').all().order_by('-created_at')

    # Annotate if any item is cancelled or return requested
    cancelled_items = OrderItem.objects.filter(order=OuterRef('pk'), status='cancelled')
    return_requested_items = OrderItem.objects.filter(order=OuterRef('pk'), status='return_requested')

    orders = orders.annotate(
        has_cancelled=Exists(cancelled_items),
        has_return_requested=Exists(return_requested_items)
    )

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

    # --- Filter by date ---
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

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
        'start_date': start_date,
        'end_date': end_date,
        'STATUS_CHOICES': Order.STATUS_CHOICES,
    }

    return render(request, 'admin/order_list.html', context)
 

@login_required(login_url='admin_login')
@never_cache
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()

    def update_order_status(order):
        """Auto-update order status based on items."""
        items = order.items.all()
        if all(item.status == "returned" for item in items):
            order.status = "returned"
        elif any(item.status == "returned" for item in items):
            order.status = "partially_returned"
        order.save(update_fields=["status"])

    if request.method == "POST":
        action = request.POST.get("action")
        status = request.POST.get("status")
        item_id = request.POST.get("item_id")

        # ✅ Update whole order status (manual)
        if status:
            order.status = status
            order.save(update_fields=['status'])
            messages.success(request, f"Order status updated to {order.get_status_display()}")
            return redirect('admin_order_detail', order_id=order.id)

        # ✅ Approve Return (whole order)
        if action == "approve_return" and not item_id:
            order.status = 'returned'
            order.return_approved = True
            order.return_approved_by = request.user
            order.return_approved_at = timezone.now()
            order.save()

            for item in order_items.filter(status='return_requested'):
                if item.variant and item.status != 'returned':
                    item.variant.stock += item.quantity
                    item.variant.save()
                item.status = 'returned'
                item.return_approved = True
                item.save()
            messages.success(request, "Return approved for the whole order.")
            return redirect('admin_order_detail', order_id=order.id)

        # ✅ Reject Return (whole order)
        if action == "reject_return" and not item_id:
            order.return_requested = False
            order.save(update_fields=['return_requested'])
            for item in order_items.filter(status='return_requested'):
                item.status = 'return_rejected'
                item.save(update_fields=['status'])
            messages.warning(request, "Whole order return request rejected.")
            return redirect('admin_order_detail', order_id=order.id)

        # ✅ Approve Return (single item)
        if action == "approve_return" and item_id:
            item = get_object_or_404(OrderItem, id=item_id, order=order)
            if item.variant and item.status == "return_requested":
                item.variant.stock += item.quantity
                item.variant.save()
            item.status = "returned"
            item.return_approved = True
            item.save()
            update_order_status(order)  # 🔑 auto update here
            messages.success(request, f"Return approved for item {item.variant}.")
            return redirect('admin_order_detail', order_id=order.id)

        # ✅ Reject Return (single item)
        if action == "reject_return" and item_id:
            item = get_object_or_404(OrderItem, id=item_id, order=order)
            item.status = "return_rejected"
            item.save(update_fields=["status"])
            update_order_status(order)  # 🔑 auto update here
            messages.warning(request, f"Return request rejected for item {item.variant}.")
            return redirect('admin_order_detail', order_id=order.id)

        # ✅ Approve Cancel (whole order)
        if action == "approve_cancel":
            order.status = 'cancelled'
            order.cancel_approved = True
            order.cancel_approved_by = request.user
            order.cancel_approved_at = timezone.now()
            order.save()

            for item in order_items.exclude(status='cancelled'):
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()
                item.status = 'cancelled'
                item.cancel_approved = True
                item.save()
            messages.success(request, "Order cancellation approved.")
            return redirect('admin_order_detail', order_id=order.id)

        # ✅ Reject Cancel (whole order)
        if action == "reject_cancel":
            order.cancel_requested = False
            order.save(update_fields=['cancel_requested'])
            for item in order_items.filter(status='cancel_requested'):
                item.status = 'active'
                item.save(update_fields=['status'])
            messages.warning(request, "Cancel request rejected.")
            return redirect('admin_order_detail', order_id=order.id)

    return render(request, 'admin/order_detail.html', {
        'order': order,
        'order_items': order_items,
    })
