from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from .forms import ProductOfferForm, CategoryOfferForm
from .models import ProductOffer, CategoryOffer

# Admin check
def is_admin(user):
    return user.is_staff or user.is_superuser

# ===== PRODUCT OFFERS =====
@login_required
@user_passes_test(is_admin)
def product_offer_list(request):
    offers = ProductOffer.objects.all().order_by('-start_date')
    now = timezone.now()
    return render(request, 'product_offer_list.html', {'offers': offers,'now':now})

@login_required
@user_passes_test(is_admin)
def product_offer_create(request):
    if request.method == 'POST':
        form = ProductOfferForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']  
            discount = form.cleaned_data['discount_percentage']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            now = timezone.now()

            
            if discount < 1 or discount > 90:
                messages.error(request, "Offer must be between 1% and 90%.")
            
            elif start_date < now:
                messages.error(request, "Start date cannot be in the past.")
            elif end_date <= start_date:
                messages.error(request, "End date must be after the start date.")

            elif ProductOffer.objects.filter(product=product, is_active=True, end_date__gte=now).exists():
                messages.error(request, "An active offer already exists for this product.")
            else:
                form.save()
                messages.success(request, "Product offer created successfully.")
                return redirect('product_offer')
        else:
            messages.error(request, "Please correct the errors below./ All fields are required ")

    else:
        form = ProductOfferForm()
    return render(request, 'add_product_offer.html', {'form': form, 'title': 'Add Product Offer'})


@login_required
@user_passes_test(is_admin)
def product_offer_edit(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)
    if request.method == 'POST':
        form = ProductOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            return redirect('product_offer')
    else:
        form = ProductOfferForm(instance=offer)
    return render(request, 'add_product_offer.html', {'form': form, 'title': 'Edit Product Offer'})

@login_required
@user_passes_test(is_admin)
def product_offer_delete(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)
    if request.method == 'POST':
        offer.delete()
        return redirect('product_offer')
    return render(request, 'product_offer_confirm_delete.html', {'offer': offer})

@login_required
@user_passes_test(is_admin)
def product_offer_toggle(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)
    offer.is_active = not offer.is_active   # flip status
    offer.save()
    return redirect('product_offer')





# ===== CATEGORY OFFERS =====
@login_required
@user_passes_test(is_admin)
def category_offer_list(request):
    offers = CategoryOffer.objects.all().order_by("-start_date")
    now = timezone.now()  
    return render(request, 'category_offer_list.html', {'offers': offers,'now':now})

from django.contrib import messages
from .models import CategoryOffer  

@login_required
@user_passes_test(is_admin)
def category_offer_create(request):
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST)
        if form.is_valid():
            category = form.cleaned_data['category']
            discount = form.cleaned_data['discount_percentage']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            now = timezone.now()  

            if discount < 1 or discount > 90:
                messages.error(request, "Offer must be between 1% and 90%.")
            elif CategoryOffer.objects.filter(category=category,end_date__gte=now).exists():
                messages.error(request, "Offer for this category already exists.")
            elif start_date < now:
                messages.error(request, "Start date cannot be in the past.")
            elif end_date <= start_date:
                messages.error(request, "End date must be after the start date.")
            else:
                form.save()
                messages.success(request, "Category offer created successfully.")
                return redirect('category_offer')
    else:
        form = CategoryOfferForm()

    return render(request, 'add_category_offer.html', {'form': form})



@login_required
@user_passes_test(is_admin)
def category_offer_edit(request, pk):
    offer = get_object_or_404(CategoryOffer, pk=pk)
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, "Category offer updated successfully.")
            return redirect('category_offer')
    else:
        form = CategoryOfferForm(instance=offer)
    return render(request, 'add_category_offer.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def category_offer_delete(request, pk):
    offer = get_object_or_404(CategoryOffer, pk=pk)
    if request.method == 'POST':
        offer.delete()
        messages.success(request, "Category offer deleted.")
        return redirect('category_offer')
    return render(request, 'category_offer_confirm_delete.html', {'offer': offer})

@login_required
@user_passes_test(is_admin)
def toggle_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    offer.is_active = not offer.is_active
    offer.save()
    messages.success(request, f"{offer.category.name} offer toggled successfully.")
    return redirect('category_offer')
