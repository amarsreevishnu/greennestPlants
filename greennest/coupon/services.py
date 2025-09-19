from django.utils import timezone
from django.utils.crypto import get_random_string
from decimal import Decimal
from .models import Coupon, CouponUsage

def create_referral_coupon(inviter):
    
    coupon = Coupon.objects.create(
        code="REF" + get_random_string(6).upper(),
        discount=Decimal("10.00"),  # fixed 10% discount
        active=True,
        valid_from=timezone.now(),
        valid_to=timezone.now() + timezone.timedelta(days=30),
        max_discount_amount=Decimal("500.00"),    # cap amount set(500rupees)
        min_order_value=Decimal("100.00"),        # 500 minmum order
        is_referral=True,
    )

    CouponUsage.objects.create(
        user=inviter,
        coupon=coupon,
        used=False
    )

    return coupon
