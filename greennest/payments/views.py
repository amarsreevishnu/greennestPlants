import razorpay
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction

from orders.models import Order
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
def razorpay_checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    razorpay_order = client.order.create({
        "amount": int(order.final_amount * 100),
        "currency": "INR",
        "payment_capture": "1"
    })

    # Create or update pending Payment
    payment, created = Payment.objects.get_or_create(
        order=order,
        user=request.user,
        method="razorpay",
        defaults={
            "amount": order.final_amount,
            "status": "pending",
            "razorpay_order_id": razorpay_order["id"],
        }
    )
    if not created:
        payment.razorpay_order_id = razorpay_order["id"]
        payment.status = "pending"
        payment.save()

    context = {
        "order": order,
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": order.final_amount,
    }
    return render(request, "razorpay_checkout.html", context)



# Razorpay Callback
@login_required
def razorpay_callback(request):
    if request.method == "POST":
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")

        payment = Payment.objects.filter(razorpay_order_id=order_id).first()
        if not payment:
            messages.error(request, "Payment record not found ❌")
            return redirect("cart_detail")

        try:
            if not payment_id or not signature:
                raise ValueError("Missing payment_id or signature")

            params_dict = {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            }
            client.utility.verify_payment_signature(params_dict)

            with transaction.atomic():
                # refetch cleanly without outer joins
                order = Order.objects.select_for_update(of=("self",)).get(id=payment.order_id)

                # ✅ Success
                payment.status = "success"
                payment.razorpay_payment_id = payment_id
                payment.razorpay_signature = signature
                payment.save()

                order.status = "processing"
                order.payment_method = "Razorpay"
                order.save()

            Cart.objects.filter(user=request.user).delete()
            request.session.pop("applied_coupon_id", None)

            messages.success(request, "Payment successful via Razorpay ✅")
            return redirect("order_success", order_id=order.id)

        except Exception as e:
            with transaction.atomic():
                order = Order.objects.get(id=payment.order_id)
                payment.status = "failed"
                payment.save()
                order.status = "failed"
                order.save()

            messages.error(request, f"Payment failed ❌ Reason: {str(e)}")
            return redirect("order_failure", order_id=order.id)

    return redirect("cart_detail")



