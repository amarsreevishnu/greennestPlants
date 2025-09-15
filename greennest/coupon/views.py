from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Coupon, CouponUsage
from offer.utils import get_best_offer
from decimal import Decimal
from cart.models import Cart 


@login_required(login_url="user_login")

def user_coupons(request):
    now = timezone.now()

    # Global coupons (valid for everyone)
    global_coupons = Coupon.objects.filter(
        active=True,
        valid_from__lte=now,
        valid_to__gte=now,
        is_referral=False
    )

    # Referral coupons (ONLY those assigned to this user)
    referral_usages = CouponUsage.objects.filter(
        user=request.user,
        coupon__active=True,
        coupon__valid_from__lte=now,
        coupon__valid_to__gte=now,
        coupon__is_referral=True
    ).select_related("coupon")

    # Build combined list with usage status
    coupon_list = []

    # Add global coupons (mark used if present in CouponUsage)
    user_usages = {
        usage.coupon_id: usage.used
        for usage in CouponUsage.objects.filter(user=request.user)
    }
    for coupon in global_coupons:
        coupon_list.append({
            "coupon": coupon,
            "used": user_usages.get(coupon.id, False),
        })

    # Add referral coupons (from this user's usages only)
    for usage in referral_usages:
        coupon_list.append({
            "coupon": usage.coupon,
            "used": usage.used,
        })

    return render(request, "user_coupons.html", {"coupon_list": coupon_list})

@login_required
def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get("coupon_code", "").strip()

        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
            return redirect("checkout_address")

        # Check coupon validity
        if not coupon.is_valid():
            messages.error(request, "Coupon is expired or inactive.")
            return redirect("checkout_address")

        # Check if user has already used it
        if CouponUsage.objects.filter(user=request.user, coupon=coupon, used=True).exists():
            messages.warning(request, "You have already used this coupon.")
            return redirect("checkout_address")

        #  Check cart subtotal against coupon min_order_value
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect("checkout_address")

        subtotal = 0
        for item in cart.items.all():
            variant = item.variant
            best_offer = get_best_offer(variant)
            final_price = best_offer["final_price"] if best_offer else variant.price
            subtotal += final_price * item.quantity

        if subtotal < coupon.min_order_value:
            messages.warning(
                request,
                f"⚠️ Minimum order of ₹{coupon.min_order_value} required to use this coupon."
            )
            # ❌ Do NOT save coupon in session
            return redirect("checkout_address")

        # ✅ Save only if all checks passed
        request.session["applied_coupon_id"] = coupon.id
        request.session.modified = True  

        messages.success(request, f"Coupon '{coupon.code}' applied ")
        return redirect("checkout_address")

    return redirect("checkout_address")


def remove_coupon(request):
    if "applied_coupon_id" in request.session:
        del request.session["applied_coupon_id"]
        messages.success(request, "Coupon removed successfully.")
    return redirect("checkout_address")
