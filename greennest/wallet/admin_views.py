from django.views.decorators.cache import never_cache
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from .models import Wallet, WalletTransaction
from django.contrib.auth import get_user_model

User = get_user_model()

def is_admin(user):
    return user.is_staff or user.is_superuser


@user_passes_test(is_admin)
@never_cache
def wallet_list(request):
    transactions = WalletTransaction.objects.select_related("wallet__user").order_by("-created_at")
    return render(request, "admin/wallet_list.html", {"transactions": transactions})

def wallet_detials(request,transaction_id):
    tx = get_object_or_404(WalletTransaction.objects.select_related("wallet__user"), id=transaction_id)
    return render(request,"admin/wallet_details.html",{"tx":tx})