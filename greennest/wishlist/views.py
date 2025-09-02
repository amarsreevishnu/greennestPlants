from django.shortcuts import render
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import WishlistItem
from products.models import ProductVariant

def wishlist_view(request):
    return render (request,'wishlist/wishlist.html')


@login_required
def toggle_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    # Check if item is already in wishlist
    wishlist_item = WishlistItem.objects.filter(user=request.user, variant=variant).first()

    if wishlist_item:
        wishlist_item.delete()  # Remove from wishlist
    else:
        WishlistItem.objects.create(user=request.user, variant=variant)  # Add to wishlist

    return redirect(request.META.get('HTTP_REFERER', '/'))  # Go back to the page user came from

@login_required
def remove_from_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    # Delete wishlist item if exists
    WishlistItem.objects.filter(user=request.user, variant=variant).delete()

    # Redirect back to wishlist page
    return redirect('wishlist_view')


def wishlist_count(request):
    if request.user.is_authenticated:
        count = WishlistItem.objects.filter(user=request.user).count()
        return JsonResponse({'count': count})
    else:
        return JsonResponse({'count': 0})
