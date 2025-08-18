from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product

# User product list
@login_required
def user_product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, "user/product_list.html", {"products": products})

# User product detail
@login_required
def user_product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    additional_images = product.images.all()


    # Similar products suggestion (same category)
    similar_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=product.pk)[:4]
    return render(request, "user/product_detail.html", {"product": product,  "similar_products": similar_products,"additional_images": additional_images})
