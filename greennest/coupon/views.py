from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Coupon, CouponUsage

def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get("coupon_code", "").strip()

        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
            return redirect("checkout_address")

        if not coupon.is_valid():
            messages.error(request, "Coupon is expired or inactive.")
            return redirect("checkout_address")

        # Check if already used
        if CouponUsage.objects.filter(user=request.user, coupon=coupon, used=True).exists():
            messages.warning(request, "You have already used this coupon.")
            return redirect("checkout_address")

        # Save coupon to session 
        request.session["applied_coupon_id"] = coupon.id
        messages.success(request, f"Coupon '{coupon.code}' applied successfully ✅")
        return redirect("checkout_address")


def remove_coupon(request):
    if "applied_coupon_id" in request.session:
        del request.session["applied_coupon_id"]
        messages.success(request, "Coupon removed successfully.")
    return redirect("checkout_address")
