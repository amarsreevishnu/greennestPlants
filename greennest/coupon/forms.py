# coupons/forms.py
from django import forms
from .models import Coupon

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ["code", "discount", "valid_from", "valid_to", "active"]

        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter Coupon Code"}),
            "discount": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Discount %"}),
            "valid_from": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "valid_to": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_discount(self):
        discount = self.cleaned_data.get("discount")
        if discount <= 0 or discount > 100:
            raise forms.ValidationError("Discount must be between 1% and 100%.")
        return discount

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get("valid_from")
        valid_to = cleaned_data.get("valid_to")

        if valid_from and valid_to and valid_from >= valid_to:
            raise forms.ValidationError("Valid From must be earlier than Valid To.")

        return cleaned_data
