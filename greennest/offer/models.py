from django.db import models
from django.utils import timezone
from products.models import Product, Category
from django.conf import settings

class ProductOffer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_offers")
    discount_percentage = models.PositiveIntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True) 

    def active(self):
        """Check if the offer is currently active and within date range."""
        return self.is_active and self.start_date <= timezone.now() <= self.end_date

    def __str__(self):
        return f"{self.discount_percentage}% off on {self.product.name}"


class CategoryOffer(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="category_offers")
    discount_percentage = models.PositiveIntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def active(self):
        return self.is_active and self.start_date <= timezone.now() <= self.end_date

    def __str__(self):
        return f"{self.discount_percentage}% off on {self.category.name}"


class Referral(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral")
    referral_code = models.CharField(max_length=10, unique=True)
    invited_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="referred_by", blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Referral({self.user.username})"
