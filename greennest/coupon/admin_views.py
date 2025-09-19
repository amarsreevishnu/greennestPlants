# coupons/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.utils import timezone
import datetime as _dt

from .models import Coupon
from .forms import CouponForm

@login_required(login_url='admin_login')
@never_cache
def coupon_list(request):
    coupons = list(Coupon.objects.filter(is_referral=False))  
    now = timezone.now()

    for c in coupons:
        c.is_expired = False
        if not c.valid_to:
            continue
        
        if isinstance(c.valid_to, _dt.date) and not isinstance(c.valid_to, _dt.datetime):
            c.is_expired = (c.valid_to < now.date())
            continue

        valid_dt = c.valid_to
       
        if timezone.is_naive(valid_dt):
            try:
                valid_dt = timezone.make_aware(valid_dt)
            except Exception:
                pass

        c.is_expired = (valid_dt <= now)
    return render(request, "admin/coupon_list.html", {"coupons": coupons})

@login_required(login_url='admin_login')
@never_cache
def coupon_create(request):
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get("code").strip()
            
            if Coupon.objects.filter(code__icontains=code).exists():
                messages.error(request, f"A coupon with similar code '{code}' already exists.")
                return render(request, "admin/coupon_form.html", {"form": form})
            
            form.save()
            messages.success(request, "Coupon created successfully.")
            return redirect("coupon_list")
    else:
        form = CouponForm()
    return render(request, "admin/coupon_form.html", {"form": form})

@login_required(login_url='admin_login')
@never_cache
def coupon_update(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            code = form.cleaned_data.get("code").strip()
            
            if Coupon.objects.filter(code__icontains=code).exclude(pk=coupon.pk).exists():
                messages.error(request, f"A coupon with similar code '{code}' already exists.")
                return render(request, "admin/coupon_form.html", {"form": form, "coupon": coupon})
            
            form.save()
            messages.success(request, "Coupon updated successfully.")
            return redirect("coupon_list")
    else:
        form = CouponForm(instance=coupon)
    return render(request, "admin/coupon_form.html", {"form": form, "coupon": coupon})


@never_cache
def coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    messages.success(request, "Coupon deleted successfully.")
    return redirect("coupon_list")
