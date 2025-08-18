from django.shortcuts import render, redirect
from products.models import Product

# Create your views here.

def home(request):
    if request.user.is_authenticated:
        return redirect('user_home')
    products = Product.objects.all()
    return render(request, "home.html", {"products": products})
    