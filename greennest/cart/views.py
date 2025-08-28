from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from products.models import ProductVariant, Product
from wishlist.models import WishlistItem
from .models import Cart, CartItem

MAX_QTY_PER_PRODUCT = 5  # Max quantity a user can add for a single variant

@login_required
def add_to_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    # Check if product or category is inactive
    if not variant.is_active or not variant.product.is_active or not variant.product.category.is_active:
        return redirect('product_list')  # or show error message

    if variant.stock == 0:
        return redirect('product_list')  # Optionally show out-of-stock message
        
    # Get or create cart
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Get or create cart item
    cart_item, created_item = CartItem.objects.get_or_create(cart=cart, variant=variant)

    if not created_item:
        # Increment quantity if stock allows
        if cart_item.quantity < variant.stock:
            cart_item.quantity += 1
            cart_item.save()
    else:
        # Ensure starting quantity does not exceed MAX_QTY_PER_PRODUCT
        if cart_item.quantity > MAX_QTY_PER_PRODUCT:
            cart_item.quantity = MAX_QTY_PER_PRODUCT
            cart_item.save()
    
    # Remove from wishlist if exists
    WishlistItem.objects.filter(user=request.user, variant=variant).delete()

    return redirect('cart_detail')


@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'cart/cart_detail.html', {'cart': cart})


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect('cart_detail')


@login_required
def update_cart_quantity(request, item_id, action):
    """Increment or decrement quantity"""
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
