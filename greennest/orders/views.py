# orders/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from cart.models import Cart, CartItem
from .models import Order, OrderItem
from users.models import Address

@login_required
def checkout(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()
    addresses = Address.objects.filter(user=user)
    
    if not cart or not cart.items.exists():
        return redirect('cart_detail')

    if request.method == 'POST':
        address_id = request.POST.get('address')
        selected_address = Address.objects.get(id=address_id, user=user)
        
        # Calculate totals
        subtotal = sum(item.variant.price * item.quantity for item in cart.items.all())
        tax = subtotal * 0.05  # Example: 5% tax
        discount = 0  # Implement discount logic if any
        shipping = 50  # Flat shipping charge
        final_amount = subtotal + tax + shipping - discount

        # Create order
        order = Order.objects.create(
            user=user,
            address=selected_address,
            total_amount=subtotal,
            tax=tax,
            discount=discount,
            shipping_charge=shipping,
            final_amount=final_amount,
            payment_method='Cash on Delivery'
        )

        # Move cart items to order items
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                quantity=item.quantity,
                price=item.variant.price,
                total_price=item.variant.price * item.quantity
            )
            # Reduce stock
            item.variant.stock -= item.quantity
            item.variant.save()

        # Clear user cart
        cart.items.all().delete()

        return redirect('order_success', order_id=order.id)

    context = {
        'cart': cart,
        'addresses': addresses
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_success(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def order_detail(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})
