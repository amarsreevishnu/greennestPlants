from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from .models import Wallet, WalletTransaction
    
import json
import razorpay
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Wallet, WalletTransaction

# Show wallet balance and transactions
@login_required
def wallet_dashboard(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().order_by("-created_at")
    return render(request, "wallet_dashboard.html", {"wallet": wallet, "transactions": transactions})


@login_required
@never_cache
def create_wallet_order(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount", 0))  

        if amount <= 0:
            return JsonResponse({"error": "Invalid amount"}, status=400)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": amount * 100,  # convert rupees to paise
            "currency": "INR",
            "payment_capture": "1"
        })

        # Save order in session (or DB if you want to track properly)
        request.session["wallet_recharge_amount"] = amount

        return JsonResponse({
            "order_id": razorpay_order["id"],
            "amount": amount * 100,
            "key_id": settings.RAZORPAY_KEY_ID,
            "name": request.user.username,
            "email": request.user.email,
        })

@csrf_exempt
@login_required
@never_cache
def verify_wallet_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"]
            })

            # Get stored amount from session (or DB)
            amount = request.session.get("wallet_recharge_amount", 0)

            if amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += amount
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type="credit",
                    amount=amount,
                    description=f"₹{amount} added via Razorpay"
                )

                # clear from session
                del request.session["wallet_recharge_amount"]

                return JsonResponse({"status": "success", "message": f"₹{amount} added to wallet ✅"})
            else:
                return JsonResponse({"status": "failed", "message": "Amount not found ❌"})
        except:
            return JsonResponse({"status": "failed", "message": "Payment verification failed ❌"})
