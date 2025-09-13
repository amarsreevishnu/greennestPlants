from django.utils import timezone
from .models import ProductOffer, CategoryOffer

def get_best_offer(variant):
    """
    Return best offer (Product Offer vs Category Offer) for a given ProductVariant.
    """
    original_price = variant.price
    now = timezone.now()

    # Get active product offers
    product_offer = (
        ProductOffer.objects.filter(
            product=variant.product,
            start_date__lte=now,
            end_date__gte=now,
            is_active=True
        ).order_by("-discount_percentage").first()
    )

    # Get active category offers
    category_offer = (
        CategoryOffer.objects.filter(
            category=variant.product.category,
            start_date__lte=now,
            end_date__gte=now,
            is_active=True
        ).order_by("-discount_percentage").first()
    )

    product_price = original_price
    category_price = original_price

    # Apply product offer
    if product_offer and 1 <= product_offer.discount_percentage <= 90:
        product_price = original_price - (original_price * product_offer.discount_percentage / 100)

    # Apply category offer
    if category_offer and 1 <= category_offer.discount_percentage <= 90:
        category_price = original_price - (original_price * category_offer.discount_percentage / 100)

    # Choose best
    if product_price <= category_price:
        final_price = product_price
        discount = product_offer.discount_percentage if product_offer else 0
        offer_type = "Product Offer" if product_offer else None
    else:
        final_price = category_price
        discount = category_offer.discount_percentage if category_offer else 0
        offer_type = "Category Offer" if category_offer else None

    return {
        "original_price": original_price,
        "final_price": round(final_price, 2),
        "discount": discount,
        "offer_type": offer_type,
    }
