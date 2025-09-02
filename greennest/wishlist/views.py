from django.shortcuts import render
from django.shortcuts import redirect, get_object_or_404
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

    context = {
        'wishlist_items': wishlist_items,
        'wishlist_count': count,
    }
    return render(request, 'wishlist/wishlist.html', context)

@login_required
@never_cache
def toggle_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    # Check if item is already in wishlist
    wishlist_item = WishlistItem.objects.filter(user=request.user, variant=variant).first()

    if wishlist_item:
        wishlist_item.delete()  # Remove from wishlist
    else:
        WishlistItem.objects.create(user=request.user, variant=variant)  

    return redirect(request.META.get('HTTP_REFERER', '/')) 

@login_required
@never_cache
def remove_from_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    # Delete wishlist item if exists
    WishlistItem.objects.filter(user=request.user, variant=variant).delete()

    return redirect('wishlist_view')

@login_required
@never_cache
def wishlist_count(request):
    count = WishlistItem.objects.filter(user=request.user).count()
    return JsonResponse({'count': count})

