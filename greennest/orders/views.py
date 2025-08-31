from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.http import HttpResponse, Http404
from django.db.models import Q

from cart.models import Cart, CartItem
from .models import Order, OrderItem
from users.models import Address
from django.utils import timezone

@login_required
def checkout_address(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()
    addresses = Address.objects.filter(user=user)

    if not cart or not cart.items.exists():
        return redirect('cart_detail')

    # Calculate totals
    cart_items = cart.items.all()
    subtotal = sum(item.variant.price * item.quantity for item in cart_items)
    shipping = 0 if subtotal <= 2500 else 50
    total = subtotal + shipping

    if request.method == "POST":
        action = request.POST.get("action")
        edit_address_id = request.POST.get("edit_address_id")  # Hidden field

        # ---------------- Add or Edit Address ----------------
        if action == "add_edit":
            full_name = request.POST.get("full_name")
            if full_name:  
                if edit_address_id and Address.objects.filter(id=edit_address_id, user=user).exists():
                    # ✅ Update existing address
                    addr = Address.objects.get(id=edit_address_id, user=user)
                    addr.full_name = full_name
                    addr.phone = request.POST.get("phone")
                    addr.line1 = request.POST.get("line1")
                    addr.line2 = request.POST.get("line2")
                    addr.city = request.POST.get("city")
                    addr.state = request.POST.get("state")
                    addr.postal_code = request.POST.get("postal_code")
                    addr.country = request.POST.get("country")
                    addr.address_type = request.POST.get("address_type")
                    addr.save()
                    messages.success(request, "Address updated successfully ✅")
                else:
                    # ✅ Always create new address (never overwrite default)
                    Address.objects.create(
                        user=user,
                        full_name=full_name,
                        phone=request.POST.get("phone"),
                        line1=request.POST.get("line1"),
                        line2=request.POST.get("line2"),
                        city=request.POST.get("city"),
                        state=request.POST.get("state"),
                        postal_code=request.POST.get("postal_code"),
                        country=request.POST.get("country"),
                        address_type=request.POST.get("address_type")
                    )
                    messages.success(request, "New address added successfully ✅")
            return redirect("checkout_address")

        # ---------------- Proceed to Payment ----------------
        elif action == "proceed":
            selected_address_id = request.POST.get("address")
            if not selected_address_id:
                messages.error(request, "⚠️ Please select an address to proceed.")
                return redirect("checkout_address")
            request.session["selected_address_id"] = selected_address_id
            return redirect("checkout_payment")

    context = {
        "cart": cart,
        "addresses": addresses,
        "subtotal": subtotal,
        "shipping": shipping,
        "total": total,
    }
    return render(request, "orders/checkout_address.html", context)


@login_required
def checkout_payment(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()
    
    if not cart or not cart.items.exists():
        return redirect('cart_detail')

    selected_address_id = request.session.get('selected_address_id')
    if not selected_address_id:
        return redirect('checkout_address')

    address = Address.objects.get(id=selected_address_id, user=user)
    cart_items = cart.items.all()
    subtotal = sum(item.variant.price * item.quantity for item in cart_items)
    shipping = 0 if subtotal <= 2500 else 50
    total = subtotal + shipping

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'Cash on Delivery')

        # Create order
        order = Order.objects.create(
            user=user,
            address=address,
            total_amount=subtotal,
            shipping_charge=shipping,
            final_amount=total,
            payment_method=payment_method
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price=item.variant.price,
                total_price=item.variant.price * item.quantity
            )
            item.variant.stock -= item.quantity
            item.variant.save()

        cart.items.all().delete()
        del request.session['selected_address_id']  # Clear session

        return redirect('order_success', order_id=order.id)

    context = {
        'cart': cart,
        'address': address,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'orders/checkout_payment.html', context)



@login_required
def order_success(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    q = request.GET.get('q', '').strip()
    orders = Order.objects.filter(user=request.user)
    if q:
        # search by id, status, variant name, or address, date
        orders = orders.filter(
            Q(id__iexact=q) |
            Q(status__icontains=q) |
            Q(address__line1__icontains=q) |
            Q(items__variant__name__icontains=q)
        ).distinct()
    orders = orders.order_by("-created_at")
    return render(request, "orders/order_list.html", {"orders": orders, "q": q})


@login_required
def order_detail(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)
    return render(request, "orders/order_detail.html", {"order": order, "items": items})


def request_cancel_order(request, order_id):
    """User requests cancellation of entire order (optional reason)."""
    order = Order.objects.filter(id=order_id, user=request.user).first()
    if not order:
        raise Http404("Order not found")

    # only allow cancel if not delivered/completed/cancelled yet
    if order.status in ['delivered', 'completed', 'cancelled', 'returned']:
        messages.error(request, "This order cannot be cancelled.")
        return redirect('order_detail', order_id=order_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip() or None
        order.cancel_requested = True
        order.cancel_reason = reason
        order.cancel_requested_at = timezone.now()
        order.save()
        messages.success(request, "Cancellation requested. Admin will review it.")
        return redirect('order_detail', order_id=order_id)

    return render(request, 'orders/request_cancel_order.html', {'order': order})

@login_required
def cancel_order(request, order_id):
    """Cancel the entire order."""

    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        id=order_id,
        user=request.user,
    )

    if order.status not in ["pending", "processing"]:
        messages.error(request, "This order cannot be cancelled anymore.")
        return redirect("order_list")

    if request.method == "POST":
        reason = request.POST.get("reason", "")

        order.status = "cancelled"
        order.cancel_reason = reason
        order.cancel_requested = False
        order.cancel_approved = True
        order.cancel_approved_at = timezone.now()
        order.save()

        for item in order.items.all():
            item.status = "cancelled"
            item.cancel_reason = reason
            item.cancel_approved = True
            item.save()

            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

        messages.success(request, "Order cancelled successfully ✅")
        return redirect("order_list")

    return render(request, "orders/confirm_cancel_order.html", {"order": order})




@login_required
def cancel_order_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if request.method == "POST":
        reason = request.POST.get("reason", "")
        item.status = "cancelled"
        item.cancel_reason = reason
        item.cancel_requested_at = timezone.now()
        item.cancel_approved = True   # if you want auto-approve for user cancellations
        item.save()

        # 🔹 Recalculate order totals after cancellation
        item.order.recalc_totals()

        # 🔹 Update order status if only some items are cancelled
        active_items = item.order.items.filter(status="active").exists()
        if not active_items:
            item.order.status = "cancelled"
        else:
            item.order.status = "partially_cancelled"
        item.order.save()

        messages.success(request, "The item has been cancelled successfully.")
        return redirect("order_detail", order_id=item.order.id)

    return render(request, "orders/confirm_cancel_item.html", {"item": item})



@login_required
def request_return_item(request, order_id, item_id):
    """User requests return for a delivered item. Reason is mandatory."""
    order = Order.objects.filter(id=order_id, user=request.user).first()
    if not order:
        raise Http404("Order not found")

    try:
        item = order.items.get(id=item_id)
    except OrderItem.DoesNotExist:
        raise Http404("Item not found")

    if order.status != 'delivered' and item.status != 'delivered':
        messages.error(request, "Return can only be requested for delivered items.")
        return redirect('order_detail', order_id=order_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for return (required).")
            return redirect('order_detail', order_id=order_id)
        item.status = 'return_requested'
        item.return_reason = reason
        item.return_requested_at = timezone.now()
        item.save()
        order.return_requested = True
        order.return_requested_at = timezone.now()
        order.save()
        messages.success(request, "Return requested. Admin will review.")
        return redirect('order_detail', order_id=order_id)

    return render(request, 'orders/request_return_item.html', {'order': order, 'item': item})


@login_required
def download_invoice(request, order_id):
    """Generate a simple PDF invoice for the order."""
    order = Order.objects.filter(id=order_id, user=request.user).first()
    if not order:
        raise Http404("Order not found")

    # create a PDF using ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from io import BytesIO

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"Invoice — Order #{order.id}")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    c.drawString(50, height - 85, f"Customer: {order.user.get_full_name() or order.user.username}")

    # address
    y = height - 110
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Shipping Address:")
    c.setFont("Helvetica", 10)
    if order.address:
        addr_lines = [
            getattr(order.address, 'full_name', ''),
            getattr(order.address, 'line1', ''),
            getattr(order.address, 'line2', ''),
            f"{getattr(order.address, 'city', '')}, {getattr(order.address, 'state', '')} {getattr(order.address, 'postal_code', '')}",
            getattr(order.address, 'country', '')
        ]
        for ln in addr_lines:
            if ln:
                y -= 12
                c.drawString(60, y, ln)

    # items table header
    y -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Item")
    c.drawString(300, y, "Qty")
    c.drawString(350, y, "Unit Price")
    c.drawString(450, y, "Total")

    # items
    c.setFont("Helvetica", 10)
    for item in order.items.all():
        y -= 16
        c.drawString(50, y, str(getattr(item.variant, 'name', str(item.variant)[:30])))
        c.drawString(300, y, str(item.quantity))
        c.drawString(350, y, f"{item.price:.2f}")
        c.drawString(450, y, f"{item.total_price:.2f}")

    # totals
    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(350, y, "Subtotal:")
    c.drawString(450, y, f"{order.total_amount:.2f}")
    y -= 16
    c.drawString(350, y, "Shipping:")
    c.drawString(450, y, f"{order.shipping_charge:.2f}")
    y -= 16
    c.drawString(350, y, "Discount:")
    c.drawString(450, y, f"{order.discount:.2f}")
    y -= 16
    c.drawString(350, y, "Tax:")
    c.drawString(450, y, f"{order.tax:.2f}")
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y, "Final Amount:")
    c.drawString(450, y, f"{order.final_amount:.2f}")

    c.showPage()
    c.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_order_{order.id}.pdf"'
    return response