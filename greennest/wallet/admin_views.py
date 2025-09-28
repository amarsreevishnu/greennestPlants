from django.views.decorators.cache import never_cache
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from .models import Wallet, WalletTransaction
from django.contrib.auth import get_user_model
from .models import AdminWallet, AdminTransaction
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.utils.dateparse import parse_date
from django.db.models import Q

User = get_user_model()

def is_admin(user):
    return user.is_staff or user.is_superuser


@user_passes_test(is_admin)
@never_cache
def wallet_list(request):
    transactions = WalletTransaction.objects.select_related("wallet__user").order_by("-created_at")
    return render(request, "admin/wallet_list.html", {"transactions": transactions})

@user_passes_test(is_admin)
@never_cache
def wallet_detials(request,transaction_id):
    tx = get_object_or_404(WalletTransaction.objects.select_related("wallet__user"), id=transaction_id)
    return render(request,"admin/wallet_details.html",{"tx":tx})



# ----------------- Admin Wallet Dashboard -----------------
@user_passes_test(is_admin)
@never_cache
def admin_wallet_dashboard(request):
    wallet = AdminWallet.objects.first()
    total_balance = wallet.balance if wallet else 0

    transactions = AdminTransaction.objects.select_related('user', 'source_order').all().order_by('-date')

    q = request.GET.get('q', '').strip()
    if q:
        filters = Q(user__username__icontains=q) | Q(transaction_type__icontains=q) | Q(source__icontains=q)
        if q.isdigit():
            filters |= Q(amount=q)
        parsed_date = parse_date(q)
        if parsed_date:
            filters |= Q(date__date=parsed_date)
        transactions = transactions.filter(filters)

    context = {
        "wallet_balance": total_balance,
        "transactions": transactions,
        "q": q,
    }
    return render(request, "admin/admin_wallet_dashboard.html", context)


# ----------------- Transaction Detail -----------------
@user_passes_test(is_admin)
@never_cache
def admin_transaction_detail(request, transaction_id):
    transaction = get_object_or_404(AdminTransaction.objects.select_related('user', 'source_order'), id=transaction_id)
    print(transaction.source_order)
   
    return render(request, "admin/admin_transaction_detail.html", {"transaction": transaction})