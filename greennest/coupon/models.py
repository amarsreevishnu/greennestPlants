from django.db import models
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Enter discount in % (e.g., 10 = 10%)"
    )
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    
    max_discount_amount = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Maximum discount amount allowed (e.g., 500 for ₹500 cap)"
    )
    min_order_value = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Minimum order subtotal required to apply coupon"
    )

    is_referral = models.BooleanField(default=False, help_text="Mark True if this is a referral-only coupon")
    
    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to
    
    def calculate_discount(self, subtotal):
        """Calculate discount amount with % cap and min order check"""
        if subtotal <= 0:
            return Decimal("0.00")

        # Check minimum order value
        if self.min_order_value and subtotal < self.min_order_value:
            return Decimal("0.00")

        discount = (subtotal * self.discount) / 100

        # Apply max cap amt if defined
        if self.max_discount_amount:
            discount = min(discount, self.max_discount_amount)

        return discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self):
        return f"{self.code} ({self.discount}% off)"
    

class CouponUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey("Coupon", on_delete=models.CASCADE)
    used = models.BooleanField(default=False)   
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "coupon") 

    def __str__(self):
        return f"{self.user.username} - {self.coupon.code} ({'used' if self.used else 'not used'})"
