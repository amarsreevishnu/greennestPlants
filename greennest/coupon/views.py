from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Coupon, CouponUsage


@login_required(login_url="user_login")
def user_coupons(request):
    now = timezone.now()
    # Get valid coupons
    coupons = Coupon.objects.filter(
        active=True,
        valid_from__lte=now,
        valid_to__gte=now,
    )

    # Get usage info for this user
    user_usages = {
        usage.coupon_id: usage.used
        for usage in CouponUsage.objects.filter(user=request.user)
    }

    # Attach status (used/available) to each coupon
    coupon_list = []
    for coupon in coupons:
        coupon_list.append({
            "coupon": coupon,
            "used": user_usages.get(coupon.id, False),
        })

    return render(request, "user_coupons.html", {"coupon_list": coupon_list})







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
