
from django.db import models
from django.conf import settings
from products.models import ProductVariant

class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'variant')

    def __str__(self):
        return f"{self.variant} in {self.user.username}'s wishlist"
