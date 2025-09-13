from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.http import JsonResponse

from .models import WishlistItem
from products.models import ProductVariant


@login_required
@never_cache
def wishlist_view(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user)
    count = wishlist_items.count()

    wishlist_with_prices = []
    for item in wishlist_items:
        variant = item.variant

        # Use centralized property for best offer
        offer_info = getattr(variant, "best_offer_info", None)
        final_price = offer_info["final_price"] if offer_info else variant.price

        wishlist_with_prices.append({
            'item': item,
            'variant': variant,
            'final_price': final_price,
            'original_price': variant.price,
        })

    context = {
        'wishlist_items': wishlist_with_prices,
        'wishlist_count': count,
    }
    return render(request, 'wishlist/wishlist.html', context)


@login_required
@never_cache
def toggle_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    wishlist_item = WishlistItem.objects.filter(user=request.user, variant=variant).first()

    if wishlist_item:
        wishlist_item.delete()
        status = "removed"
    else:
        WishlistItem.objects.create(user=request.user, variant=variant)
        status = "added"

    count = WishlistItem.objects.filter(user=request.user).count()

    # ✅ Always return JSON
    return JsonResponse({"status": status, "count": count})


@login_required
@never_cache
def remove_from_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    WishlistItem.objects.filter(user=request.user, variant=variant).delete()
    return redirect('wishlist_view')


@login_required
@never_cache
def wishlist_count(request):
    count = WishlistItem.objects.filter(user=request.user).count()
    return JsonResponse({'count': count})
