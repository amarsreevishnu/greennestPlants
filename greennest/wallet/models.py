from django.db import models
from django.conf import settings
from django.utils import timezone

from orders.models import Order

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₹{self.balance}"

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=[("credit", "Credit"), ("debit", "Debit")])
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} ₹{self.amount} ({self.wallet.user.username})"


class AdminWallet(models.Model):
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Admin Wallet Balance: {self.balance}"


class AdminTransaction(models.Model):
    TRANSACTION_TYPES = (
        ("CREDIT", "Credit"),   
        ("DEBIT", "Debit"),     
    )
    SOURCES = (
        ("ORDER", "Order Payment"),
        ("CANCEL", "Order Cancelled"),
        ("REFUND", "Refund"),
        ("COD", "Cash on Delivery"),
    )

    id = models.AutoField(primary_key=True)
    date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=50, choices=SOURCES)
    description = models.TextField(blank=True, null=True)

    source_order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)


    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.source})"
    
    