from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.http import JsonResponse

from products.models import ProductVariant
from wishlist.models import WishlistItem
from .models import Cart, CartItem

MAX_QTY_PER_PRODUCT = 5  

@login_required
@never_cache
def add_to_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if not variant.is_active or not variant.product.is_active or not variant.product.category.is_active:
        return redirect('user_product_list')

    if variant.stock == 0:
        return redirect('user_product_list')

    cart, _ = Cart.objects.get_or_create(user=request.user)

    # ✅ Get quantity from form (default = 1)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1

    # ✅ Ensure within limits
    quantity = min(quantity, variant.stock, MAX_QTY_PER_PRODUCT)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

    if created:
        cart_item.quantity = quantity
    else:
        # Increase by selected quantity but not exceed stock/MAX_QTY
        cart_item.quantity = min(cart_item.quantity + quantity, variant.stock, MAX_QTY_PER_PRODUCT)

    cart_item.save()

    # Remove from wishlist automatically
    WishlistItem.objects.filter(user=request.user, variant=variant).delete()

    return redirect('cart_detail')



@login_required
@never_cache
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()

    subtotal = 0
    total_discount = 0
    grand_total = 0
    out_of_stock_items = False  


    for item in cart_items:
        variant = item.variant
        offer_info = getattr(variant, "best_offer_info", None)  # centralized offer info
        final_price = offer_info["final_price"] if offer_info else variant.price

        # annotate item for template
        item.offer_applied = offer_info
        item.discounted_price = final_price
        item.final_total = final_price * item.quantity  
       
        # --- STOCK CHECK ---
        if variant.stock == 0 or item.quantity > variant.stock:
            item.is_available = False
            out_of_stock_items = True
        else:
            item.is_available = True


        subtotal += variant.price * item.quantity
        total_discount += (variant.price - final_price) * item.quantity
        grand_total += item.final_total

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "total_discount": total_discount,
        "grand_total": grand_total + getattr(cart, "shipping_charge", 0),
        "out_of_stock_items": out_of_stock_items,
    }

    return render(request, "cart/cart_detail.html", context)


@login_required
@never_cache
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    next_url = request.POST.get('next') or request.GET.get('next')
    return redirect(next_url or 'cart_detail')




@login_required
@never_cache
def update_cart_quantity(request, item_id, action):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    if action == "increment" and item.quantity < item.variant.stock and item.quantity < MAX_QTY_PER_PRODUCT:
        item.quantity += 1
        item.save()
    elif action == "decrement" and item.quantity > 1:
        item.quantity -= 1
        item.save()

    # ✅ Recalculate cart totals
    cart = item.cart
    cart_items = cart.items.all()

    subtotal = 0
    total_discount = 0
    grand_total = 0

    for ci in cart_items:
        variant = ci.variant
        offer_info = getattr(variant, "best_offer_info", None)
        final_price = offer_info["final_price"] if offer_info else variant.price

        subtotal += variant.price * ci.quantity
        total_discount += (variant.price - final_price) * ci.quantity
        grand_total += final_price * ci.quantity

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "item_id": item.id,
            "quantity": item.quantity,
            "item_total": item.quantity * (getattr(item.variant, "best_offer_info", {"final_price": item.variant.price})["final_price"]),
            "subtotal": subtotal,
            "total_discount": total_discount,
            "grand_total": grand_total + getattr(cart, "shipping_charge", 0),
            "can_increment": item.quantity < item.variant.stock and item.quantity < MAX_QTY_PER_PRODUCT,
        })

    return redirect("cart_detail")