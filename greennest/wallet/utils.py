from decimal import Decimal
from .models import AdminWallet, AdminTransaction

def get_admin_wallet():
    wallet, _ = AdminWallet.objects.get_or_create(id=1)
    return wallet

def add_to_admin_wallet(user, amount, source, description="",source_order=None):
    wallet = get_admin_wallet()
    wallet.balance = Decimal(wallet.balance)
    wallet.balance += Decimal(amount)
    wallet.save()
    AdminTransaction.objects.create(
        user=user,
        transaction_type="CREDIT",
        amount=amount,
        source=source,
        description=description,
        source_order=source_order,
    )

def deduct_from_admin_wallet(user, amount, source, description="",source_order=None):
    wallet = get_admin_wallet()
    wallet.balance -= Decimal(amount)
    wallet.save()
    AdminTransaction.objects.create(
        user=user,
        transaction_type="DEBIT",
        amount=amount,
        source=source,
        description=description,
        source_order=source_order,
    )
