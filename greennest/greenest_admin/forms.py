from django import forms
from .models import Banner

class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ['title', 'subtitle', 'image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'subtitle': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter subtitle'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
