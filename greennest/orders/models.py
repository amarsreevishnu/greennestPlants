from django.db import models
from django.conf import settings

from products.models import ProductVariant
from users.models import Address
from coupon.models import Coupon
from offer.models import ProductOffer, CategoryOffer

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('partially_cancelled', 'Partially Cancelled'),
        ('return_requested', 'Return Requested'),
        ('returned', 'Returned'),
        ("partially_returned", "Partially Returned"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    payment_method = models.CharField(max_length=50, default='Cash on Delivery')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # Cancellation / Return request info (user side)
    cancel_requested = models.BooleanField(default=False)
    cancel_reason = models.TextField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)

    cancel_approved = models.BooleanField(default=False)
    cancel_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_cancels')
    cancel_approved_at = models.DateTimeField(null=True, blank=True)

    return_requested = models.BooleanField(default=False)
    return_reason = models.TextField(null=True, blank=True)
    return_requested_at = models.DateTimeField(null=True, blank=True)

    return_approved = models.BooleanField(default=False)
    return_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_returns')
    return_approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def recalc_totals(self):
        """ Recalculate subtotal, apply coupon discount, and update final total """
        items = self.items.filter(status__in=["active", "delivered"])
        subtotal = sum(item.total_price for item in items)

        self.total_amount = subtotal

        # If coupon applied, discount comes from coupon, else keep current discount
        if self.coupon and self.coupon.is_valid():
            self.discount = self.coupon.calculate_discount(subtotal)
        else:
            self.discount = 0

        self.final_amount = max(subtotal + self.shipping_charge + self.tax - self.discount, 0)
        self.save()


    @property
    def display_id(self):
        """Custom display ID: OID + order id + date in DDMMYYYY format with month as number"""
        return f"OID{self.id}-{self.created_at.strftime('%d%m%Y')}"

class OrderItem(models.Model):
    ITEM_STATUS = [
        ('active', 'Active'),
        ('cancel_requested', 'Cancel Requested'),
        ('cancelled', 'Cancelled'),
        ('delivered', 'Delivered'),
        ('return_requested', 'Return Requested'),
        ('returned', 'Returned'),
        ("return_rejected", "Return Rejected"),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)  
    total_price = models.DecimalField(max_digits=10, decimal_places=2) 

    # status + reasons
    status = models.CharField(max_length=20, choices=ITEM_STATUS, default='active')
    cancel_reason = models.TextField(null=True, blank=True)   
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    cancel_approved = models.BooleanField(default=False)

    return_reason = models.TextField(null=True, blank=True)   
    return_requested_at = models.DateTimeField(null=True, blank=True)
    return_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    