from django.db import models
from django.conf import settings
from products.models import ProductVariant

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    def total_price(self):
        return sum(item.total_price() for item in self.items.all())
    
    @property
    def shipping_charge(self):
        """Shipping: Free if subtotal > 500, else ₹50"""
        return 0 if self.total_price() > 500 else 50
    
    @property
    def grand_total(self):
        """Subtotal + shipping"""
        return self.total_price() + self.shipping_charge

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'variant')

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    def total_price(self):
        return self.variant.price * self.quantity
