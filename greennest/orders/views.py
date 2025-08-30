from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from cart.models import Cart, CartItem
from .models import Order, OrderItem
from users.models import Address


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
    """Show all orders of the logged-in user"""
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)
    return render(request, "orders/order_detail.html", {"order": order, "items": items})
