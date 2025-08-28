from django.shortcuts import render

# Create your views here.

def wishlist_view(request):
    return render (request,'wishlist.html')