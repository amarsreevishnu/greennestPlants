
from django.db import models
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Enter discount in % (e.g., 10 = 10%)")
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to
    
    def calculate_discount(self, subtotal):
        """Calculate discount amount based on percentage"""
        if subtotal <= 0:
            return 0
        discount = (subtotal * self.discount) / 100
        return discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def __str__(self):
        return f"{self.code} ({self.discount_percent}% off)"

class CouponUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey("coupon.Coupon", on_delete=models.CASCADE)
    used = models.BooleanField(default=False)   
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "coupon") 

    def __str__(self):
        return f"{self.user.username} - {self.coupon.code} ({'used' if self.used else 'not used'})"