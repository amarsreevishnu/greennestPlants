from django.shortcuts import render, redirect
from django.db.models import Min

from products.models import Product


# Create your views here.

def home(request):
    if request.user.is_authenticated:
        return redirect('user_home')
    products = Product.objects.prefetch_related("variants__images").annotate(
        min_price=Min("variants__price")  
    )

    # Attach a main_image property 
    for product in products:
        
        cheapest_variant = (
            product.variants.order_by("price").prefetch_related("images").first()
        )
        if cheapest_variant and cheapest_variant.images.exists():
            product.main_image = cheapest_variant.images.first()  
        else:
            product.main_image = None  

    
    return render(request, "home.html", {"products": products})
    