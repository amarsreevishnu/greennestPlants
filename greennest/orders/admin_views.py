from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db.models import Q, Exists, OuterRef
from django.contrib import messages
from django.utils import timezone
from orders.models import Order, OrderItem


from django.db.models import Sum, Count
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from django.db.models import Q, Exists, OuterRef
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from orders.models import Order, OrderItem
from wallet.models import Wallet, WalletTransaction


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

        # --- Update whole order status (manual) ---
        if status:
            order.status = status
            order.save(update_fields=['status'])
            messages.success(request, f"Order status updated to {order.get_status_display()}")
            return redirect('admin_order_detail', order_id=order.id)

        # --- Approve Return (whole order) ---
        if action == "approve_return" and not item_id:
            order.status = 'returned'
            order.return_approved = True
            order.return_approved_by = request.user
            order.return_approved_at = timezone.now()
            order.save()

            refund_amount = 0
            for item in order_items.filter(status='return_requested'):
                if item.variant and item.status != 'returned':
                    item.variant.stock += item.quantity
                    item.variant.save()
                item.status = 'returned'
                item.return_approved = True 
                item.save()
                refund_amount += item.price  

            # --- Credit refund to wallet ---
            if refund_amount > 0:
                wallet, created = Wallet.objects.get_or_create(user=order.user)
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type="credit",
                    description=f"Refund for returned Order #{order.display_id  }"
                )
                messages.success(request, f"Return approved. ₹{refund_amount} refunded to {order.user.full_name}'s wallet.")
            else:
                messages.success(request, "Return approved for the whole order (no refund).")

            return redirect('admin_order_detail', order_id=order.id)

        # --- Reject Return (whole order) ---
        if action == "reject_return" and not item_id:
            order.return_requested = False
            order.save(update_fields=['return_requested'])
            for item in order_items.filter(status='return_requested'):
                item.status = 'return_rejected'
                item.save(update_fields=['status'])
            messages.warning(request, "Whole order return request rejected.")
            return redirect('admin_order_detail', order_id=order.id)

        # --- Approve Return (single item) ---
        if action == "approve_return" and item_id:
            item = get_object_or_404(OrderItem, id=item_id, order=order)
            if item.variant and item.status == "return_requested":
                item.variant.stock += item.quantity
                item.variant.save()
            item.status = "returned"
            item.return_approved = True
            item.save()

            # --- Refund single item ---
            refund_amount = item.price
            if refund_amount > 0:
                wallet, created = Wallet.objects.get_or_create(user=order.user)
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type="credit",
                    description=f"Refund for returned item {item.variant} in Order #{order.display_id}"
                )
                messages.success(request, f"Return approved. ₹{refund_amount} refunded to {order.user.username}'s wallet.")
            else:
                messages.success(request, f"Return approved for item {item.variant} (no refund).")

            update_order_status(order)  
            return redirect('admin_order_detail', order_id=order.id)

        # --- Reject Return (single item) ---
        if action == "reject_return" and item_id:
            item = get_object_or_404(OrderItem, id=item_id, order=order)
            item.status = "return_rejected"
            item.save(update_fields=["status"])
            update_order_status(order)  
            messages.warning(request, f"Return request rejected for item {item.variant}.")
            return redirect('admin_order_detail', order_id=order.id)

        # --- Approve Cancel (whole order) ---
        if action == "approve_cancel":
            order.status = 'cancelled'
            order.cancel_approved = True
            order.cancel_approved_by = request.user
            order.cancel_approved_at = timezone.now()
            order.save()

            refund_amount = 0
            for item in order_items.exclude(status='cancelled'):
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()
                item.status = 'cancelled'
                item.cancel_approved = True
                item.save()
                refund_amount += item.price  

            # --- Credit refund to wallet ---
            if refund_amount > 0:
                wallet, created = Wallet.objects.get_or_create(user=order.user)
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type="credit",
                    description=f"Refund for cancelled Order #{order.display_id}"
                )
                messages.success(request, f"Order cancelled. ₹{refund_amount} refunded to {order.user.first_name}'s wallet.")
            else:
                messages.success(request, "Order cancellation approved (no refund).")

            return redirect('admin_order_detail', order_id=order.id)

        # --- Reject Cancel (whole order) ---
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




@login_required(login_url='admin_login')
@never_cache
def sales_report(request):
    # only completed/delivered orders count as sales
    orders = Order.objects.filter(status__in=["completed", "delivered"])

    # summary numbers
    total_orders = orders.count()
    total_revenue = orders.aggregate(Sum("final_amount"))["final_amount__sum"] or 0
    total_discount = orders.aggregate(Sum("discount"))["discount__sum"] or 0
    total_tax = orders.aggregate(Sum("tax"))["tax__sum"] or 0
    total_shipping = orders.aggregate(Sum("shipping_charge"))["shipping_charge__sum"] or 0

    # date filters
    today = datetime.today().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)

    daily_sales = orders.filter(created_at__date=today).aggregate(Sum("final_amount"))["final_amount__sum"] or 0
    weekly_sales = orders.filter(created_at__date__gte=last_week).aggregate(Sum("final_amount"))["final_amount__sum"] or 0
    monthly_sales = orders.filter(created_at__date__gte=last_month).aggregate(Sum("final_amount"))["final_amount__sum"] or 0

    # custom date range filter
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    filtered_orders = orders
    if start_date and end_date:
        filtered_orders = orders.filter(
            created_at__date__range=[start_date, end_date]
        )

    context = {
        "orders": filtered_orders,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_discount": total_discount,
        "total_tax": total_tax,
        "total_shipping": total_shipping,
        "daily_sales": daily_sales,
        "weekly_sales": weekly_sales,
        "monthly_sales": monthly_sales,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "admin/sales_report.html", context)




from django.utils.dateparse import parse_date

def download_sales_report_pdf(request):
    orders = Order.objects.filter(status__in=["completed", "delivered"])

    # Apply custom date range filter (same as sales_report)
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date and end_date:
        orders = orders.filter(
            created_at__date__range=[parse_date(start_date), parse_date(end_date)]
        )

    # Create a PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, height - 50, "Sales Report")

    # Date
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 80, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Summary
    total_orders = orders.count()
    total_revenue = orders.aggregate(Sum("final_amount"))["final_amount__sum"] or 0
    total_discount = orders.aggregate(Sum("discount"))["discount__sum"] or 0
    total_tax = orders.aggregate(Sum("tax"))["tax__sum"] or 0
    total_shipping = orders.aggregate(Sum("shipping_charge"))["shipping_charge__sum"] or 0

    y = height - 120
    summary = [
        f"Total Orders: {total_orders}",
        f"Total Revenue: Rs.{total_revenue:.2f}",
        f"Total Discount: Rs.{total_discount:.2f}",
        f"Total Tax: Rs.{total_tax:.2f}",
        f"Total Shipping: Rs.{total_shipping:.2f}",
    ]
    p.setFont("Helvetica", 11)
    for line in summary:
        p.drawString(50, y, line)
        y -= 20

    # Table Header
    y -= 20
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Order ID")
    p.drawString(150, y, "User")
    p.drawString(230, y, "Status")
    p.drawString(330, y, "Final Amount")
    p.drawString(400, y, "Date")
    y -= 15
    p.line(50, y, 500, y)
    y -= 15

    p.setFont("Helvetica", 10)
    if start_date and end_date:
        p.drawString(50, height - 95, f"Date Range: {start_date} to {end_date}")
        
    # Orders list
    p.setFont("Helvetica", 9)
    for order in orders:
        if y < 80:  
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 9)

        p.drawString(50, y, str(order.display_id))
        p.drawString(150, y, str(order.user.first_name))
        p.drawString(230, y, str(order.status))
        p.drawString(330, y, f"Rs.{order.final_amount:.2f}")
        p.drawString(400, y, order.created_at.strftime("%Y-%m-%d"))
        y -= 20

    p.save()
    buffer.seek(0)

    # Return response
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="sales_report.pdf"'
    return response
