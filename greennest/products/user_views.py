from django.shortcuts import redirect, render
from django.urls import reverse  
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Min, Max
from django.db.models import Min, Max, Prefetch
from django.utils import timezone

from cart.models import Cart
from .models import Product, ProductVariant, Category
from offer.models import ProductOffer, CategoryOffer
from offer.utils import get_best_offer



# User product list
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
    
    # Variant queryset to prefetch
    variant_qs = ProductVariant.objects.filter(
        is_active=True,
        stock__gt=0  # Only variants with stock
    ).order_by("price")

    # Product queryset
    products = Product.objects.filter(
        is_active=True,
        variants__stock__gt=0
    ).prefetch_related(
        Prefetch("variants", queryset=variant_qs, to_attr="available_variants")
    ).annotate(
        min_price=Min("variants__price"),
        max_price=Max("variants__price"),
    ).distinct()

    # Wishlist variant ids for the current user
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
        products = products.order_by("min_price")
    elif sort_option == "price_desc":
        products = products.order_by("-max_price")

    products = products.prefetch_related("variants__images")

    # Pagination
    page = request.GET.get("page", 1)
    paginator = Paginator(products, 9)
    page_obj = paginator.get_page(page)

    # AJAX response for Load More
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = []
        for product in page_obj:
            variant = product.available_variants[0] if hasattr(product, "available_variants") and product.available_variants else None
            if variant:
                # Get best offer
                best_offer = get_best_offer(product)
                if best_offer:
                    discount = (variant.price * best_offer.discount_percentage) / 100
                    offer_price = variant.price - discount
                    price_display = f"₹ {offer_price:.0f}"
                else:
                    price_display = f"₹ {variant.price:.0f}"

                stock = variant.stock
                image_obj = variant.images.first()
                image_url = image_obj.image.url if image_obj else "/static/images/no-image.png"
            else:
                price_display = "Price not available"
                stock = 0
                image_url = "/static/images/no-image.png"

            data.append({
                "id": product.id,
                "name": product.name,
                "price": price_display,
                "variant_stock": stock,
                "variant_image": image_url,
                "detail_url": reverse("user_product_detail", args=[product.id]),
                "variant_id": variant.id if variant else None,
                "in_wishlist": variant.id in wishlist_variant_ids if variant else False,
                "wishlist_url": reverse("toggle_wishlist", args=[variant.id]) if variant else "#"
            })
        return JsonResponse({"products": data, "has_next": page_obj.has_next()})

    # Annotate discounted price for normal page render
    for product in page_obj:
        variant = product.available_variants[0] if hasattr(product, "available_variants") and product.available_variants else None
        if variant:
            best_offer = get_best_offer(product)
            if best_offer:
                discount = (variant.price * best_offer.discount_percentage) / 100
                variant.discounted_price = variant.price - discount
            else:
                variant.discounted_price = variant.price

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
        'wishlist_variant_ids': wishlist_variant_ids,
    }
    return render(request, "user/product_list.html", context)


# User product detail
@login_required(login_url='user_login')
@never_cache
def user_product_detail(request, pk):
    product = Product.objects.filter(pk=pk, is_active=True).first()
    if not product:
        messages.warning(request, "This product is unavailable.")
        return redirect("user_product_list")

    # Fetch variants ordered by price ascending
    variants = product.variants.order_by('price').prefetch_related('images')
    cheapest_variant = variants.first()

      # ✅ Get best offer
    best_offer = get_best_offer(product)

    # ✅ Annotate each variant with discounted price
    for variant in variants:
        if best_offer:
            discount = (variant.price * best_offer.discount_percentage) / 100
            variant.discounted_price = variant.price - discount
        else:
            variant.discounted_price = variant.price

    # ✅ Cheapest variant discounted price
    discounted_price = None
    if cheapest_variant and best_offer:
        discount = (cheapest_variant.price * best_offer.discount_percentage) / 100
        discounted_price = cheapest_variant.price - discount



    main_image = None
    additional_images = []

    if cheapest_variant:
        images = list(cheapest_variant.images.all())
        if images:
            main_image = images[0]
            additional_images = images[0:4]

    if cheapest_variant and cheapest_variant.stock > 0:
        stock_status = "In Stock"
    else:
        stock_status = "Out of Stock"

    # Similar products for the same category excluding current product
    similar_products = (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(pk=product.pk)
        .prefetch_related('variants__images')
        .order_by("?")[:4]
    )
    
    cart, created = Cart.objects.get_or_create(user=request.user)

    

    context = {
        "product": product,
        "variants": variants,
        "cheapest_variant": cheapest_variant,
        "main_image": main_image,
        "additional_images": additional_images,
        "similar_products": similar_products,
        "stock_status": stock_status, 
        'cart': cart,
        "best_offer": best_offer,                 
        "discounted_price": discounted_price,     
    }
    return render(request, "user/product_detail.html", context)