from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wallet, WalletTransaction

# Show wallet balance and transactions
@login_required
def wallet_dashboard(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().order_by("-created_at")
    return render(request, "wallet_dashboard.html", {"wallet": wallet, "transactions": transactions})


# Add money to wallet
@login_required
def add_money(request):
    if request.method == "POST":
        amount = float(request.POST.get("amount", 0))
        if amount > 0:
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="credit",
                amount=amount,
                description="Money added to wallet"
            )

            messages.success(request, f"₹{amount} added to wallet successfully ✅")
            return redirect("wallet_dashboard")
        else:
            messages.error(request, "Invalid amount entered ❌")

    return render(request, "    add_money.html")
