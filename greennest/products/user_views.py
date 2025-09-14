from django.shortcuts import redirect, render
from django.urls import reverse  
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Min, Max, Prefetch

from cart.models import Cart
from wishlist.models import WishlistItem
from .models import Product, ProductVariant, Category
from offer.utils import get_best_offer


@login_required(login_url='user_login')
@never_cache
def user_product_list(request):
    search_query = request.GET.get("q", "")
    categories = request.GET.getlist("category") 
    sizes = request.GET.getlist("sizes")  
    lights = request.GET.getlist("lights")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    sort_option = request.GET.get("sort", "")

    # Prefetch variants with stock
    variant_qs = ProductVariant.objects.filter(
        is_active=True, stock__gt=0
    ).order_by("price")

    products = Product.objects.filter(
        is_active=True,
        variants__stock__gt=0
    ).prefetch_related(
        Prefetch("variants", queryset=variant_qs, to_attr="available_variants"),
        "variants__images"
    ).distinct()

    # Wishlist variant ids
    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist_variant_ids = request.user.wishlist_items.all().values_list('variant_id', flat=True)

    # Filters
    if search_query:
        products = products.filter(name__icontains=search_query)
    if categories:
        products = products.filter(category__name__in=categories)
    if sizes:
        products = products.filter(size__in=sizes)
    if lights:
        products = products.filter(light_requirement__in=lights)
    if min_price:
        products = products.filter(variants__price__gte=min_price).distinct()
    if max_price:
        products = products.filter(variants__price__lte=max_price).distinct()

    # Sorting
    if sort_option == "name_asc":
        products = products.order_by("name")
    elif sort_option == "name_desc":
        products = products.order_by("-name")
    elif sort_option == "price_asc":
        products = products.annotate(min_price=Min("variants__price")).order_by("min_price")
    elif sort_option == "price_desc":
        products = products.annotate(max_price=Max("variants__price")).order_by("-max_price")

    # Pagination
    page = request.GET.get("page", 1)
    paginator = Paginator(products, 9)
    page_obj = paginator.get_page(page)

    # AJAX Load More
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = []
        for product in page_obj:
            variant = product.available_variants[0] if getattr(product, "available_variants", None) else None
            if variant:
                offer_info = variant.best_offer_info
                stock = variant.stock
                image_obj = variant.images.first()
                image_url = image_obj.image.url if image_obj else "/static/images/no-image.png"

                # Build HTML for price/offer, same as in template
                if offer_info and offer_info["final_price"] < variant.price:
                    discount_percent = offer_info.get("discount_percent", None)
                    price_html = f"""
                    <span class="text-danger fw-bold">₹ {offer_info['final_price']:.0f}</span>
                    <del class="text-muted">₹ {variant.price:.0f}</del>
                    
                    """
                    if discount_percent:
                        price_html += f"""
                        <span class="badge bg-warning">
                            ({discount_percent}% OFF)
                        </span>
                        """
                else:
                    price_html = f"<span>₹ {variant.price:.0f}</span>"


            else:
                stock = 0
                image_url = "/static/images/no-image.png"
                price_html = "<span>Price not available</span>"

            data.append({
                "id": product.id,
                "name": product.name,
                "price_html": price_html,   
                "variant_stock": stock,
                "variant_image": image_url,
                "detail_url": reverse("user_product_detail", args=[product.id]),
                "variant_id": variant.id if variant else None,
                "in_wishlist": variant.id in wishlist_variant_ids if variant else False,
                "wishlist_url": reverse("toggle_wishlist", args=[variant.id]) if variant else "#"
            })
        return JsonResponse({"products": data, "has_next": page_obj.has_next()})


    # Pass context for normal render
    all_categories = Category.objects.filter(is_active=True)
   
    context = {
        "products": page_obj,
        "search_query": search_query,
        "categories": categories,
        "all_categories": all_categories, 
        "sizes": sizes,
        "lights": lights,
        "min_price": min_price,
        "max_price": max_price,
        "sort_option": sort_option,
        "wishlist_variant_ids": list(wishlist_variant_ids),
        
    }
    return render(request, "user/product_list.html", context)


@login_required(login_url='user_login')
@never_cache
def user_product_detail(request, pk):
    product = Product.objects.filter(pk=pk, is_active=True).first()
    if not product:
        messages.warning(request, "This product is unavailable.")
        return redirect("user_product_list")

    # Variants ordered by price
    variants = product.variants.filter(is_active=True).order_by("price").prefetch_related("images")
    cheapest_variant = variants.first()

    # Best offer for cheapest variant
    best_offer = cheapest_variant.best_offer_info if cheapest_variant else None
    discounted_price = best_offer["final_price"] if best_offer else (cheapest_variant.price if cheapest_variant else None)

    # Main image + additional images
    main_image = cheapest_variant.images.first() if cheapest_variant and cheapest_variant.images.exists() else None
    additional_images = list(cheapest_variant.images.all()[:4]) if cheapest_variant else []

    stock_status = "In Stock" if cheapest_variant and cheapest_variant.stock > 0 else "Out of Stock"

    # Similar products
    similar_products = (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(pk=product.pk)
        .prefetch_related('variants__images')
        .order_by("?")[:4]
    )

    cart, _ = Cart.objects.get_or_create(user=request.user)
    wishlist_variant_ids = WishlistItem.objects.filter(user=request.user).values_list('variant_id', flat=True)

    context = {
        "product": product,
        "variants": variants,
        "cheapest_variant": cheapest_variant,
        "main_image": main_image,
        "additional_images": additional_images,
        "similar_products": similar_products,
        "stock_status": stock_status,
        "cart": cart,
        "best_offer": best_offer,
        "discounted_price": discounted_price,
        "wishlist_variant_ids": list(wishlist_variant_ids),
    }
    return render(request, "user/product_detail.html", context)
