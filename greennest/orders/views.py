
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from django.utils.dateparse import parse_date
from offer.utils import get_best_offer
from django.utils import timezone
from django.http import HttpResponse, Http404
from django.db.models import Q, Prefetch
from django.contrib import messages

from .models import Order, OrderItem
from cart.models import Cart, CartItem
from users.models import Address
from wallet.models import Wallet, WalletTransaction
from coupon.models import Coupon, CouponUsage

from django.db import transaction
from django.db.models import F
from decimal import Decimal, ROUND_HALF_UP
from django.utils.text import slugify
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from io import BytesIO

@login_required
@never_cache
def checkout_address(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()
    addresses = Address.objects.filter(user=user)
    now = timezone.now()
    global_coupons =( Coupon.objects.filter(active=True, valid_to__gte=now, is_referral=False).exclude(id__in=CouponUsage.objects.filter(user=request.user).values_list("coupon_id", flat=True)))
    user_coupons = Coupon.objects.filter(couponusage__user=request.user,couponusage__used=False,active=True,valid_to__gte=now, is_referral=True)
    coupons = (user_coupons | global_coupons).distinct()
    
    if not cart or not cart.items.exists():
        return redirect('cart_detail')

    for item in cart.items.all():
        if item.variant.stock < item.quantity:
            messages.error(request, f"{item.variant.product.name} is out of stock.")
            return redirect("cart_detail")
        
    # Calculate totals
    cart_items = cart.items.all()
    subtotal = 0
    for item in cart.items.all():
        variant = item.variant
        best_offer = get_best_offer(variant)   
        product_price = variant.price
        discount_amount = 0
        if best_offer:
            discount_amount = (product_price * best_offer["discount"]) / 100  

        final_price = best_offer["final_price"] if best_offer else product_price

        item.offer_applied = best_offer["offer_type"] if best_offer else None
        item.discounted_price = final_price
        item.final_total = final_price * item.quantity

        subtotal += item.final_total
    shipping = 0 if subtotal > 500 else 50
    discount = 0
    total = subtotal + shipping - discount
    applied_coupon = None

    # Check session for applied coupon
    
    coupon_id = request.session.get("applied_coupon_id")
    if coupon_id:
        try:
            applied_coupon = Coupon.objects.get(id=coupon_id, active=True)
            if applied_coupon.is_valid():
                if subtotal >= applied_coupon.min_order_value:
                    discount = applied_coupon.calculate_discount(subtotal)
                else:
                    messages.warning(
                        request, 
                        f"⚠️ Minimum order of ₹{applied_coupon.min_order_value} required to use this coupon."
                    )
                    request.session.pop("applied_coupon_id", None)  
                    applied_coupon = None
            else:
                request.session.pop("applied_coupon_id", None)
        except Coupon.DoesNotExist:
            request.session.pop("applied_coupon_id", None)


    total = subtotal + shipping - discount
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
    
    selected_address_id = request.session.get("selected_address_id")
    if not selected_address_id and addresses.exists():
        default_address = addresses.filter(is_default=True).first()  
        if default_address:
            selected_address_id = default_address.id
            request.session["selected_address_id"] = selected_address_id

    context = {
        "cart": cart,
        "addresses": addresses,
        "subtotal": subtotal,
        "shipping": shipping,
        "discount": discount,
        "total": total,
        "applied_coupon": applied_coupon,
        "selected_address_id": selected_address_id,
        "coupons": coupons,
    }
    return render(request, "orders/checkout_address.html", context)

# used for auto slect addres(ajax)
@login_required
@never_cache
def save_selected_address(request):
    if request.method == "POST":
        address_id = request.POST.get("address_id")
        if Address.objects.filter(id=address_id, user=request.user).exists():
            request.session["selected_address_id"] = address_id
    return HttpResponse(status=200)



@login_required
@never_cache
def checkout_payment(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()

    if not cart or not cart.items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart_detail")

    # --- Calculate totals ---
    subtotal = 0
    for item in cart.items.all():
        variant = item.variant
        best_offer = get_best_offer(variant)
        product_price = variant.price
        final_price = best_offer["final_price"] if best_offer else product_price
        subtotal += final_price * item.quantity

    shipping = 0 if subtotal > 500 else 50
    discount = 0
    applied_coupon = None
    coupon_id = request.session.get("applied_coupon_id")
    if coupon_id:
        applied_coupon = Coupon.objects.filter(id=coupon_id, active=True).first()
        if applied_coupon and applied_coupon.is_valid():
            discount = applied_coupon.calculate_discount(subtotal)

    total = subtotal + shipping - discount

    if request.method == "POST":
        address_id = request.POST.get("address_id") or request.session.get("selected_address_id")
        payment_method = request.POST.get("payment_method")

        if not address_id:
            messages.error(request, "Please select an address.")
            return redirect("checkout_payment")

        selected_address = get_object_or_404(Address, id=address_id, user=user)

        if payment_method == "wallet":
            wallet, _ = Wallet.objects.get_or_create(user=user)
            if wallet.balance < total:
                messages.error(request, "Insufficient wallet balance to complete this order.")
                return redirect("checkout_payment")

        if payment_method == "cod" and total > 1000:
            messages.error(request, "Cash on Delivery is not available for orders above ₹1000.")
            return redirect("checkout_payment")

        # For COD and Wallet → create order immediately
        if payment_method in ["cod", "wallet"]:
            try:
                with transaction.atomic():
                    order_status = "processing"
                    order = Order.objects.create(
                        user=user,
                        address=selected_address,
                        total_amount=subtotal,
                        shipping_charge=shipping,
                        discount=discount,
                        final_amount=total,
                        coupon=applied_coupon,
                        status=order_status,
                        payment_method=payment_method,
                    )

                    # Deduct stock + create order items
                    for item in cart.items.select_related("variant").select_for_update():
                        variant = item.variant
                        variant.refresh_from_db()
                        if variant.stock is not None and variant.stock >= item.quantity:
                            variant.stock -= item.quantity
                            variant.save()
                        else:
                            messages.error(request, f"Insufficient stock for {variant.name}")
                            raise ValueError("Stock error")

                        best_offer = get_best_offer(variant)
                        product_price = variant.price
                        final_price = best_offer["final_price"] if best_offer else product_price

                        OrderItem.objects.create(
                            order=order,
                            variant=variant,
                            quantity=item.quantity,
                            price=final_price,
                            total_price=final_price * item.quantity,
                        )

                    # Mark coupon usage
                    if applied_coupon:
                        CouponUsage.objects.update_or_create(
                            user=user,
                            coupon=applied_coupon,
                            defaults={"used": True, "used_at": timezone.now()},
                        )

                    # Clear cart
                    cart.delete()
                    request.session.pop("applied_coupon_id", None)
                    request.session.pop("selected_address_id", None)

                if payment_method == "cod":
                    return redirect("cod_payment", order_id=order.id)
                else:
                    return redirect("wallet_payment", order_id=order.id)

            except Exception as e:
                messages.error(request, f"Could not place order: {str(e)}")
                return redirect("checkout_payment")

        # For Razorpay → defer order creation
        elif payment_method == "razorpay":
            
            request.session['razorpay_cart_data'] = {
                "subtotal": str(subtotal),  
                "shipping": str(shipping),
                "discount": str(discount),
                "total": str(total),
                "address_id": selected_address.id,
                "coupon_id": applied_coupon.id if applied_coupon else None,
            }
            return redirect("razorpay_checkout")

        else:
            messages.error(request, "Invalid payment method.")
            return redirect("checkout_payment")

    # Handle selected address
    selected_address_id = request.session.get("selected_address_id")
    selected_address = None
    if selected_address_id:
        selected_address = Address.objects.filter(id=selected_address_id, user=user).first()
    else:
        selected_address = Address.objects.filter(user=user, default=True).first()
        if selected_address:
            request.session["selected_address_id"] = selected_address.id

    return render(request, "orders/checkout_payment.html", {
        "cart": cart,
        "subtotal": subtotal,
        "shipping": shipping,
        "discount": discount,
        "total": total,
        "applied_coupon": applied_coupon,
        "selected_address": selected_address,
    })




@login_required
@never_cache
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status not in ["processing", "confirmed"]:
        return redirect("order_failure", order_id=order.id)

    return render(request, "orders/order_success.html", {"order": order})



@login_required
@never_cache
def razorpay_failed_payment(request):
    # No order yet, so just show generic failure
    return render(request, "orders/razorpay_failed.html")


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
    items = order.items.all()

    # Billable items only
    billable_items = items.exclude(status__in=["cancelled", "returned"])
    subtotal = sum(item.total_price for item in billable_items)

    # Handle shipping charge
    if not billable_items.exists():
        shipping = Decimal("0.00")   
    else:
        shipping = order.shipping_charge or Decimal("0.00")

    coupon_discount = Decimal("0.00")
    other_discount = Decimal("0.00")

    # Separate discounts if needed
    if order.coupon:
        coupon_discount = min(order.discount, subtotal)  
    if hasattr(order, "other_discount") and order.other_discount:
        other_discount = order.other_discount

    total = subtotal - coupon_discount - other_discount + shipping

    # Flags for UI actions
    for item in items:
        item.can_return = (item.status == "delivered")
        item.return_requested_display = (item.status == "return_requested")

    return render(request, "orders/order_detail.html", {
        "order": order,
        "items": items,
        "subtotal": subtotal,
        "shipping": shipping,
        "coupon_discount": coupon_discount,
        "other_discount": other_discount,
        "total": total,
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

        # Mark order as cancelled
        order.status = "cancelled"
        order.cancel_reason = reason
        order.cancel_requested = False
        order.cancel_approved = True
        order.cancel_approved_at = timezone.now()
        order.save()

        # Cancel all items + restore stock
        for item in order.items.all():
            item.status = "cancelled"
            item.cancel_reason = reason
            item.cancel_approved = True
            item.save()

            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

        # Refund if prepaid (exclude COD)
        if order.payment_method.lower() not in ["cod", "cash on delivery"]:
            refund_amount = order.final_amount

            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            wallet.balance += refund_amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="credit",
                amount=refund_amount,
                description=f"Refund for cancelled Order #{order.display_id}"
            )

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
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()

        active_items_exist = order.items.filter(status="active").exists()

        # --- Refund Calculation ---
        if not active_items_exist:
            
            refund_amount = order.final_amount
        else:
            
            item_total = item.quantity * item.price

            if order.discount > 0 and order.subtotal > 0:
                
                discount_share = (item_total / order.subtotal) * order.discount
            else:
                discount_share = 0

            refund_amount = item_total - discount_share

        # --- Refund to wallet if prepaid ---
        if order.payment_method.lower() not in ["cod", "cash on delivery"]:
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            wallet.balance += refund_amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="credit",
                amount=refund_amount,
                description=(
                    f"Refund for full Order #{order.display_id}"
                    if not active_items_exist
                    else f"Refund for cancelled item in Order #{order.display_id}"
                )
            )

        # Recalculate totals
        order.recalc_totals()

        order.status = "cancelled" if not active_items_exist else "partially_cancelled"
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


# invoice download (PDF)-----------------------------------------------

@login_required
def download_invoice(request, order_id):
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.all()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Register font
    font_name_to_use = "Arial"
    pdfmetrics.registerFont(TTFont("Arial", "arial.ttf"))
    p.setFont(font_name_to_use, 12)

    def q2(val):
        return Decimal(val).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    items_to_show = items.exclude(status__in=["cancelled", "returned"])

    # --- Totals ---
    if items_to_show.exists():
        subtotal = sum(item.total_price for item in items_to_show)
        tax = sum(q2(item.total_price * getattr(item.variant.product, "tax_rate", 0) / 100)
                  for item in items_to_show)
        shipping = order.shipping_charge or Decimal("0.00")
    else:
        subtotal = Decimal("0.00")
        tax = Decimal("0.00")
        shipping = Decimal("0.00")

    # --- Discounts ---
    coupon_discount = Decimal("0.00")
    other_discount = getattr(order, "other_discount", Decimal("0.00"))

    if order.coupon and subtotal > 0:
        original_subtotal = sum(item.price * item.quantity for item in items)
        coupon_discount = (subtotal / original_subtotal * order.discount) if original_subtotal > 0 else order.discount

    # --- Final Amount ---
    final_amount = q2(subtotal + shipping - coupon_discount - other_discount + tax)

    # ------------------ HEADER ------------------
    company_name = "GreenNest Pvt Ltd"
    company_address = "123, MG Road, TVPM, Kerala, 682001"
    company_phone = "+91-9876543210"
    company_email = "greennest.ecom@gmail.com"

    p.setFont(font_name_to_use, 14)
    p.drawCentredString(width / 2, height - 50, company_name)

    p.setFont(font_name_to_use, 10)
    p.drawCentredString(width / 2, height - 65, company_address)
    p.drawCentredString(width / 2, height - 80, f"Phone: {company_phone} | Email: {company_email}")

    p.setLineWidth(1)
    p.line(40, height - 90, width - 40, height - 90)

    p.setFont(font_name_to_use, 14)
    if order.status.lower() == "delivered":
        title_text = f"Invoice No: {order.display_id}"
    else:
        title_text = f"Order Summary ({order.status.capitalize()})"
    p.drawCentredString(width / 2, height - 110, title_text)

    p.setFont(font_name_to_use, 10)
    p.drawString(50, height - 115, f"Date: {order.created_at.strftime('%d %b %Y')}")
    p.drawString(50, height - 130, f"Status: {order.status}")

    # ------------------ CUSTOMER ADDRESS ------------------
    y = height - 160
    p.setFont(font_name_to_use, 12)
    p.drawString(50, y, "Shipping Address:")
    y -= 15
    p.setFont(font_name_to_use, 10)
    p.drawString(50, y, order.address.full_name)
    y -= 15
    p.drawString(50, y, f"{order.address.line1}, {order.address.line2}")
    y -= 15
    p.drawString(50, y, f"{order.address.city}, {order.address.state}")
    y -= 15
    p.drawString(50, y, f"Phone: {order.address.phone}")

    # ------------------ ITEMS TABLE ------------------
    y -= 30
    p.setFont(font_name_to_use, 12)
    p.drawString(50, y, "Product")
    p.drawString(250, y, "Price")
    p.drawString(350, y, "Qty")
    p.drawString(400, y, "Total")
    y -= 20

    p.setFont(font_name_to_use, 10)

    for item in items_to_show:
        p.drawString(50, y, f"{item.variant.product.name} ({item.variant.variant_type})")
        p.drawRightString(320, y, f"{item.price:.2f}")
        p.drawRightString(370, y, str(item.quantity))
        p.drawRightString(470, y, f"{item.total_price:.2f}")
        y -= 15
        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont(font_name_to_use, 10)

    # ------------------ TOTALS ------------------
    y -= 20
    line_height = 15
    p.setFont(font_name_to_use, 10)

    p.drawString(350, y, "Subtotal:")
    p.drawRightString(width - 50, y, f"{subtotal:.2f}")
    y -= line_height

    p.drawString(350, y, "Shipping:")
    p.drawRightString(width - 50, y, f"{shipping:.2f}")
    y -= line_height

    if coupon_discount > 0:
        p.drawString(350, y, "Coupon Discount:")
        p.drawRightString(width - 50, y, f"-{coupon_discount:.2f}")
        y -= line_height

    if other_discount > 0:
        p.drawString(350, y, "Other Discount:")
        p.drawRightString(width - 50, y, f"-{other_discount:.2f}")
        y -= line_height

    p.drawString(350, y, "Tax:")
    p.drawRightString(width - 50, y, f"{tax:.2f}")
    y -= line_height + 5

    p.setFont(font_name_to_use, 12)
    if order.status.lower() == "delivered":
        p.drawString(350, y, "Final Amount:")
        p.drawRightString(width - 50, y, f"{final_amount:.2f}")
    else:
        p.drawString(350, y, "Payable Amount:")
        p.drawRightString(width - 50, y, f"{final_amount:.2f}")

    # ------------------ FOOTER ------------------
    p.setFont(font_name_to_use, 8)
    p.drawString(50, 50, "Thank you for shopping with us!")

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    filename = "invoice" if order.status.lower() == "delivered" else "order_summary"
    response["Content-Disposition"] = f'attachment; filename="{filename}_{order.display_id}.pdf"'
    return response

