from django.db import models
from django.conf import settings
from orders.models import Order

class Payment(models.Model):
    METHOD_CHOICES = [
        ("cod", "Cash on Delivery"),  
        ("wallet", "Wallet"),
        ("razorpay", "Razorpay"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Generic transaction ID (for COD / Wallet / Other)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    # Razorpay specific fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)

    # Refund tracking
    refund_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.id} | {self.order.display_id} | {self.method} - {self.amount} ({self.status})"
