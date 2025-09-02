
from .models import WishlistItem

def wishlist_count(request):
    if request.user.is_authenticated:
        return {'wishlist_count': WishlistItem.objects.filter(user=request.user).count()}
    return {'wishlist_count': 0}
