from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

from products.models import ProductVariant, Product
from wishlist.models import WishlistItem
from .models import Cart, CartItem

MAX_QTY_PER_PRODUCT = 5  

@login_required
@never_cache
def add_to_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if not variant.is_active or not variant.product.is_active or not variant.product.category.is_active:
        return redirect('product_list')  

    if variant.stock == 0:
        return redirect('product_list')  
        
    # Get or create cart
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Get or create cart item
    cart_item, created_item = CartItem.objects.get_or_create(cart=cart, variant=variant)

    if not created_item:
        if cart_item.quantity < variant.stock:
            cart_item.quantity += 1
            cart_item.save()
    else:
        if cart_item.quantity > MAX_QTY_PER_PRODUCT:
            cart_item.quantity = MAX_QTY_PER_PRODUCT
            cart_item.save()
    
    # Remove from wishlist if exists
    WishlistItem.objects.filter(user=request.user, variant=variant).delete()

    return redirect('cart_detail')


@login_required
@never_cache
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
    })


@login_required
@never_cache
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('cart_detail')


@login_required
@never_cache
def update_cart_quantity(request, item_id, action):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if action == 'increment':
        if item.quantity < item.variant.stock and item.quantity < MAX_QTY_PER_PRODUCT:
            item.quantity += 1
            item.save()
    elif action == 'decrement':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
    return redirect('cart_detail')
