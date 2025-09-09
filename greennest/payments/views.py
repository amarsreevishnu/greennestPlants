import razorpay
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings


from orders.models import Order
from payments.models import Payment
from wallet.models import Wallet, WalletTransaction
from cart.models import Cart

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# COD Payment
@login_required
def cod_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    
    payment = Payment.objects.create(
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

   
    

    messages.success(request, "Order placed successfully with COD ✅")
    return redirect("order_success", order_id=order.id)


# Wallet Payment
@login_required
def wallet_payment(request, order_id):
    user = request.user
    cart = Cart.objects.filter(user=user).first()
    order = get_object_or_404(Order, id=order_id, user=request.user)
    wallet = getattr(request.user, "wallet", None)

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
        description=f"Payment for Order #{order.id}"
    )

    # Create Payment linked with WalletTransaction
    Payment.objects.create(
        order=order,
        user=request.user,
        method="wallet",
        amount=order.final_amount,
        status="success",
        transaction_id=f"WALLET-{tx.id}"
    )

    order.status = "processing"
    order.payment_method = "Wallet"
    order.save()

    


    messages.success(request, "Order placed using Wallet ✅")
    return redirect("order_success", order_id=order.id)


# Razorpay Payment (Initiate Checkout)
@login_required
def razorpay_checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    # Create Razorpay order
    razorpay_order = client.order.create({
        "amount": int(order.final_amount * 100),  # amount in paisa
        "currency": "INR",
        "payment_capture": "1"
    })

    # Save a pending payment with Razorpay order ID
    Payment.objects.create(
        order=order,
        user=request.user,
        method="razorpay",
        amount=order.final_amount,
        status="pending",
        razorpay_order_id=razorpay_order["id"]
    )

    context = {
        "order": order,
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": order.final_amount,
    }
    return render(request, "razorpay_checkout.html", context)


# Razorpay Callback (after payment success/failure)
@login_required
def razorpay_callback(request):
    if request.method == "POST":
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        payment = Payment.objects.filter(razorpay_order_id=order_id).first()

        if not payment:
            messages.error(request, "Payment record not found ❌")
            return redirect("cart_detail")

        order = payment.order  # keep reference here

        try:
            # If any of the required fields are missing, treat as failed
            if not payment_id or not signature:
                raise ValueError("Missing payment_id or signature")

            # Verify payment signature (raises exception if invalid)
            client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            })

            # ✅ Mark success
            payment.status = "success"
            payment.razorpay_payment_id = payment_id
            payment.razorpay_signature = signature
            payment.save()

            order.status = "processing"
            order.payment_method = "Razorpay"
            order.save()

            messages.success(request, "Payment successful via Razorpay ✅")
            return redirect("order_success", order_id=order.id)

        except Exception as e:
            # ❌ Mark failed
            payment.status = "failed"
            payment.save()

            order.status = "failed"
            order.save()

            messages.error(request, f"Payment failed ❌ Reason: {str(e)}")
            return redirect("order_failure", order_id=order.id)

    # If not POST
    return redirect("cart_detail")


