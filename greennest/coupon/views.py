
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Coupon
from orders.models import Order

def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get("coupon_code", "").strip()
        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
            return redirect("checkout")

        if not coupon.is_valid():
            messages.error(request, "Coupon is expired or inactive.")
            return redirect("checkout")

        order = Order.objects.get(user=request.user, status="pending")  # adjust query
        if order.coupon:  
            messages.warning(request, "You already applied a coupon.")
            return redirect("checkout")

        order.coupon = coupon
        order.update_totals()
        messages.success(request, f"Coupon '{coupon.code}' applied successfully!")
        return redirect("checkout")


def remove_coupon(request):
    order = Order.objects.get(user=request.user, status="pending")  # adjust query
    if order.coupon:
        order.coupon = None
        order.update_totals()
        messages.success(request, "Coupon removed successfully.")
    return redirect("checkout")
