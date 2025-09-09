# offers/utils.py
from django.utils import timezone
from .models import ProductOffer, CategoryOffer

def get_best_offer(product):
    """Return the best available offer for a product (product vs category)."""
    now = timezone.now()
    product_offer = ProductOffer.objects.filter(
        product=product, start_date__lte=now, end_date__gte=now, is_active=True
    ).order_by("-discount_percentage").first()

    category_offer = CategoryOffer.objects.filter(
        category=product.category, start_date__lte=now, end_date__gte=now, is_active=True
    ).order_by("-discount_percentage").first()

    if product_offer and category_offer:
        return product_offer if product_offer.discount_percentage >= category_offer.discount_percentage else category_offer
    return product_offer or category_offer
