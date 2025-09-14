import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone


from .models import ProductOffer, CategoryOffer



class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = ProductOffer
        fields = ['product', 'discount_percentage', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = ['category', 'discount_percentage', 'start_date', 'end_date', 'is_active']
        widgets = {
            
            'start_date': forms.DateInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateInput(attrs={'type': 'datetime-local'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['discount_percentage'].widget.attrs.update({'class': 'form-control'})
        self.fields['start_date'].widget.attrs.update({'class': 'form-control'})
        self.fields['end_date'].widget.attrs.update({'class': 'form-control'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

    def clean(self):
        cleaned = super().clean() 
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        discount = cleaned.get('discount_percentage')

        
        
        
        if start and end and end < start:
            raise ValidationError("End date cannot be before start date.")

        if discount is not None:
            if discount < 1 or discount > 90:
                self.add_error('discount_percentage', 'Discount must be between 1 and 90 percent.')

        return cleaned