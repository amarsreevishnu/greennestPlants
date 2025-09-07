
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.http import HttpResponse, Http404
from django.db.models import Q, Prefetch

from cart.models import Cart, CartItem
from .models import Order, OrderItem
from users.models import Address
from wallet.models import Wallet, WalletTransaction



@login_required
@never_cache
def checkout_address(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()
    addresses = Address.objects.filter(user=user)

    if not cart or not cart.items.exists():
        return redirect('cart_detail')

    # Calculate totals
    cart_items = cart.items.all()
    subtotal = cart.total_price()
    shipping = 0 if subtotal > 500 else 50
    total = subtotal + shipping

    if request.method == "POST":
        action = request.POST.get("action")
        edit_address_id = request.POST.get("edit_address_id")  

        # ---------------- Add or Edit Address ----------------
        if action == "add_edit":
            full_name = request.POST.get("full_name")
            if full_name:  
                if edit_address_id and Address.objects.filter(id=edit_address_id, user=user).exists():
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
                    # Always create new address (never overwrite default)
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
@never_cache
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
    subtotal = cart.total_price()
    shipping = 0 if subtotal >= 500 else 50
    total = subtotal + shipping

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')

        # Create order (not paid yet)
        order = Order.objects.create(
            user=user,
            address=address,
            total_amount=subtotal,
            shipping_charge=shipping,
            final_amount=total,
            payment_method=payment_method,
            status="pending"  # stays pending until payment succeeds
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price=item.variant.price,
                total_price=item.variant.price * item.quantity
            )
            # reduce stock (to avoid oversell, restore if payment fails)
            item.variant.stock -= item.quantity
            item.variant.save()

        # clear cart
        cart.items.all().delete()
        del request.session['selected_address_id']

        # Redirect to correct payment flow
        if payment_method == "cod":
            return redirect("cod_payment", order_id=order.id)
        elif payment_method == "wallet":
            return redirect("wallet_payment", order_id=order.id)
        elif payment_method == "razorpay":
            return redirect("razorpay_checkout", order_id=order.id)
        else:
            messages.error(request, "Invalid payment method selected")
            return redirect("checkout_payment")

    context = {
        'cart': cart,
        'address': address,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    }
    return render(request, 'orders/checkout_payment.html', context)


@login_required
@never_cache
def order_success(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})

@login_required
@never_cache
def order_failure(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/order_failure.html", {"order": order})



@login_required
@never_cache
def order_list(request):
    q = request.GET.get('q', '').strip()

    item_qs = OrderItem.objects.select_related('variant__product')
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related(Prefetch('items', queryset=item_qs))
    )

    if q:
        filters = (
            Q(status__icontains=q) |
            Q(address__line1__icontains=q) |
            Q(items__variant__product__name__icontains=q)
        )

        if q.isdigit():
            filters |= Q(id=int(q))

        parsed_date = parse_date(q)
        if parsed_date:
            filters |= Q(created_at__date=parsed_date)

        orders = orders.filter(filters).distinct()

    orders = orders.order_by("-created_at")
    return render(request, "orders/order_list.html", {"orders": orders, "q": q})


@login_required
@never_cache
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)

    for item in items:
        item.can_return = (item.status == "delivered")
        item.return_requested_display = (item.status == "return_requested")

    return render(request, "orders/order_detail.html", {
        "order": order,
        "items": items,
    })


#Cancel the entire order
@login_required
@never_cache
def cancel_order(request, order_id):
   
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
@never_cache
def cancel_order_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = item.order

    if request.method == "POST":
        reason = request.POST.get("reason", "")
        item.status = "cancelled"
        item.cancel_reason = reason
        item.cancel_requested_at = timezone.now()
        item.cancel_approved = True
        item.save()

        # Increment stock
        item.variant.stock += item.quantity
        item.variant.save()

        # Check if any active items remain
        active_items_exist = order.items.filter(status="active").exists()

        # Determine refund amount
        if not active_items_exist:
            # All items cancelled → refund full order including shipping, tax, discount
            refund_amount = order.final_amount
        else:
            # Partial cancellation → refund only cancelled item
            refund_amount = item.quantity * item.price

        # Refund only if prepaid
        if order.payment_method in ["Wallet", "Razorpay", "Paypal"]:
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            wallet.balance += refund_amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="credit",
                amount=refund_amount,
                description=f"Refund for {'full order' if not active_items_exist else 'cancelled item'} in Order #{order.display_id}"
            )

        # Recalculate order totals
        order.recalc_totals()

        # Update order status
        if not active_items_exist:
            order.status = "cancelled"
        else:
            order.status = "partially_cancelled"
        order.save()

        messages.success(request, "The item has been cancelled successfully.")
        return redirect("order_detail", order_id=order.id)

    return render(request, "orders/confirm_cancel_item.html", {"item": item})


#User requests return for the whole order (all delivered items)
@login_required
@never_cache
def request_return_order(request, order_id):
    
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != "delivered":
        messages.error(request, "Return can only be requested for delivered orders.")
        return redirect("order_detail", order_id=order_id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Please provide a reason for return (required).")
            return redirect("order_detail", order_id=order_id)

        for item in order.items.filter(status="delivered"):
            item.status = "return_requested"
            item.return_reason = reason
            item.return_requested_at = timezone.now()
            item.save()

        order.status = "return_requested"
        order.return_requested = True
        order.return_reason = reason
        order.return_requested_at = timezone.now()
        order.save()

        messages.success(request, "Return requested for the whole order. Admin will review.")
        return redirect("order_detail", order_id=order_id)

    return render(request, "orders/request_return_order.html", {"order": order})

#User requests return for a specific item (goes to admin approval).
@login_required
@never_cache
def request_return_item(request, order_id, item_id):
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)  

    # Only delivered items can be requested for return
    if order.status != "delivered":
        messages.error(request, "This item cannot be returned.")
        return redirect("order_detail", order_id=order_id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Please provide a reason for return.")
            return redirect("request_return_item", order_id=order.id, item_id=item.id)
        
        item.status = "return_requested"  
        item.return_reason = reason
        item.return_requested_at = timezone.now()
        item.save()

        order.return_requested = True
        order.save(update_fields=["return_requested"])

        messages.success(request, "Return request submitted ✅. Admin will review it.")
        return redirect("order_detail", order_id=order.id)

    return render(request, "orders/request_return_item.html", {"order": order, "item": item})


#Generate a simple PDF invoice for the order.
@login_required
@never_cache
def download_invoice(request, order_id):

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
    c.drawString(50, height - 50, f"Invoice — Order #{order.display_id}")
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
            getattr(order.address, 'phone', ''),
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
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y, "Status:")
    c.drawString(450, y, str(order.status).capitalize())


    c.showPage()
    c.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_order_{order.id}.pdf"'
    return response