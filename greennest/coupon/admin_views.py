# coupons/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Coupon
from .forms import CouponForm

def coupon_list(request):
    coupons = Coupon.objects.all()
    return render(request, "admin/coupon_list.html", {"coupons": coupons})

def coupon_create(request):
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon created successfully.")
            return redirect("coupon_list")
    else:
        form = CouponForm()
    return render(request, "admin/coupon_form.html", {"form": form})

def coupon_update(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated successfully.")
            return redirect("coupon_list")
    else:
        form = CouponForm(instance=coupon)
    return render(request, "admin/coupon_form.html", {"form": form, "coupon": coupon})

def coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    messages.success(request, "Coupon deleted successfully.")
    return redirect("coupon_list")
