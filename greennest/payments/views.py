from datetime import timezone
import razorpay
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from decimal import Decimal

from coupon.models import Coupon, CouponUsage
from offer.utils import get_best_offer
from users.models import Address
from orders.models import Order, OrderItem
from payments.models import Payment
from wallet.models import Wallet, WalletTransaction
from cart.models import Cart


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# COD Payment
@login_required
def cod_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    Payment.objects.create(
        order=order,
        user=request.user,
        method="cod",
        amount=order.final_amount,  
        status="success",
        transaction_id=f"COD-{order.id}"
    )

    order.status = "processing"
    order.payment_method = "Cash on Delivery"
    order.save()

    Cart.objects.filter(user=request.user).delete()
    request.session.pop("applied_coupon_id", None)

    messages.success(request, "Order placed successfully with COD ✅")
    return redirect("order_success", order_id=order.id)




# Wallet Payment
@login_required
def wallet_payment(request, order_id):
    user = request.user
    order = get_object_or_404(Order, id=order_id, user=user)
    wallet = getattr(user, "wallet", None)

    if not wallet or wallet.balance < order.final_amount:
        messages.error(request, "⚠️ Insufficient wallet balance.")
        return redirect("checkout_payment")

    # Deduct wallet balance
    wallet.balance -= order.final_amount
    wallet.save()

    tx = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="debit",
        amount=order.final_amount,
        description=f"Payment for Order #{order.display_id}"
    )

    Payment.objects.create(
        order=order,
        user=user,
        method="wallet",
        amount=order.final_amount,
        status="success",
        transaction_id=f"WALLET-{tx.id}"
    )

    order.status = "processing"
    order.payment_method = "Wallet"
    order.save()

    # Clear cart & coupon
    Cart.objects.filter(user=user).delete()
    request.session.pop("applied_coupon_id", None)

    messages.success(request, "Order placed using Wallet ✅")
    return redirect("order_success", order_id=order.id)


# Razorpay Checkout
@login_required
@login_required
def razorpay_checkout(request):
    cart_data = request.session.get('razorpay_cart_data')
    if not cart_data:
        messages.error(request, "Session expired. Please try again.")
        return redirect("checkout_payment")

    # Convert amounts from string to Decimal
    total_amount = Decimal(cart_data['total'])

    # Convert to paise
    amount_in_paise = int(total_amount * 100)

    amount_in_rupees = amount_in_paise / 100

    # Create Razorpay order
    razorpay_order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "payment_capture": "1"
    })

    # Create pending Payment without order yet
    payment = Payment.objects.create(
        user=request.user,
        method="razorpay",
        amount=total_amount,
        status="pending",
        razorpay_order_id=razorpay_order["id"],
    )

    context = {
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount_in_paise": amount_in_paise,
        "amount_in_rupees": amount_in_rupees,
    }
    return render(request, "razorpay_checkout.html", context)



# Razorpay Callback
@login_required
def razorpay_callback(request):
    if request.method != "POST":
        return redirect("checkout_payment")

    payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    signature = request.POST.get("razorpay_signature")

    payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
    if not payment:
        messages.error(request, "Payment record not found ❌")
        return redirect("checkout_payment")

    try:
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }
        client.utility.verify_payment_signature(params_dict)

        with transaction.atomic():
            # Fetch session data
            cart_data = request.session.get('razorpay_cart_data')
            if not cart_data:
                raise ValueError("Session expired")

            # Create Order
            order = Order.objects.create(
                user=request.user,
                address_id=cart_data['address_id'],
                total_amount=Decimal(cart_data['subtotal']),
                shipping_charge=Decimal(cart_data['shipping']),
                discount=Decimal(cart_data['discount']),
                final_amount=Decimal(cart_data['total']),
                coupon_id=cart_data.get('coupon_id'),
                status='processing',
                payment_method='Razorpay',
            )

            # Deduct stock & create OrderItems
            cart = Cart.objects.filter(user=request.user).first()
            if not cart:
                raise ValueError("Cart not found")

            for item in cart.items.select_related("variant").select_for_update():
                variant = item.variant
                variant.refresh_from_db()
                if variant.stock is not None and variant.stock >= item.quantity:
                    variant.stock -= item.quantity
                    variant.save()
                else:
                    raise ValueError(f"Insufficient stock for {variant.name}")

                best_offer = get_best_offer(variant)
                final_price = best_offer["final_price"] if best_offer else variant.price

                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=item.quantity,
                    price=final_price,
                    total_price=final_price * item.quantity,
                )

            # Mark coupon usage
            if cart_data.get('coupon_id'):
                CouponUsage.objects.update_or_create(
                    user=request.user,
                    coupon_id=cart_data['coupon_id'],
                    defaults={"used": True, "used_at": timezone.now()},
                )

            # Update Payment
            payment.status = "success"
            payment.razorpay_payment_id = payment_id
            payment.razorpay_signature = signature
            payment.order = order
            payment.save()

            # Clear cart & session
            cart.delete()
            request.session.pop('razorpay_cart_data', None)
            request.session.pop("applied_coupon_id", None)
            request.session.pop("selected_address_id", None)

        messages.success(request, "Payment successful via Razorpay ✅")
        return redirect("order_success", order_id=order.id)

    except Exception as e:
        payment.status = "failed"
        payment.save()
        messages.error(request, f"Payment failed ❌ Reason: {str(e)}")
        return redirect("checkout_payment")
