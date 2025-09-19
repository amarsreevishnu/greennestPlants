import base64
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Category, Product, ProductVariant, VariantImage
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from itertools import zip_longest
from django.contrib import messages
from io import BytesIO
from django.db.models import Q
from functools import wraps



# Check admin 

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return redirect("/greennest_admin/")  
    return _wrapped_view


# Product List
@login_required(login_url='admin_login')
@never_cache
def admin_product_list(request):
    search_query = request.GET.get('search', '')  

    # Filter products by name if search query exists
    if search_query:
        products = Product.objects.filter(name__icontains=search_query).prefetch_related("variants__images").order_by("-id")
    else:
        products = Product.objects.prefetch_related("variants__images").order_by("-id")
    
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'search_query': search_query,  
    }
    return render(request, 'admin/list_product.html', context)



# Add Product (with variants + images)

@admin_required
@never_cache
def admin_add_product(request):
    if request.method == "POST":
        category_id = request.POST.get("category")
        name = request.POST.get("name")
        description = request.POST.get("description")
        watering=request.POST.get('watering')
        light_requirement = request.POST.get("light_requirement")
        is_active = request.POST.get("is_active") == "on"

        

        if not name:
            messages.errors.append(request,"Name is required.")
            return redirect('admin_add_product')
        elif not re.match(r'^[A-Za-z ]+$', name):
            messages.errors(request,"Name should only contain letters and spaces.")
            return redirect('admin_add_product')
        if len(name)<3:
            messages.error(request,"name length must be at least Three.")
            return redirect('admin_add_product')
        

        category = get_object_or_404(Category, id=category_id,is_active=True)

        # Create product
        product = Product.objects.create(
            category=category,
            name=name,
            description=description,
            watering=watering,
            light_requirement=light_requirement,
            is_active=is_active
        )

        # Handle Variants (dynamic)
        variant_types = request.POST.getlist("variant_type[]")
        prices = request.POST.getlist("price[]")
        stocks = request.POST.getlist("stock[]")
        

        for idx, (vt, price, stock) in enumerate(zip_longest(variant_types, prices, stocks, fillvalue=None)):
            if vt and price:
                variant = ProductVariant.objects.create(
                product=product,
                variant_type=vt,
                price=price,
                stock=stock or 0
                )
            cropped_saved = False
            for i in range(3):
                cropped_img = request.POST.get(f"variant_{idx}_cropped_{i}")
                print(cropped_img)
                if cropped_img and ";base64," in cropped_img:
                    try:
                        format, imgstr = cropped_img.split(";base64,")
                        ext = format.split("/")[-1]
                        img_data = ContentFile(base64.b64decode(imgstr), name=f"variant_{variant.id}_{i}.{ext}")
                        VariantImage.objects.create(variant=variant, image=img_data)
                        cropped_saved = True
                    except Exception as e:
                        print("Crop decode error:", e, "data:", cropped_img[:30])
            # Fallback to uploaded images only if no cropped images saved
            if not cropped_saved:
                uploaded_images = request.FILES.getlist(f"variant_images_{idx}")
                for i, img in enumerate(uploaded_images[:3]):
                    VariantImage.objects.create(variant=variant, image=img)

                        
           

        return redirect("admin_product_list")

    #category to show option only ture case
    categories = Category.objects.filter(is_active=True)

    return render(request, "admin/add_product.html", {
        "categories": categories,
    })


@admin_required
@never_cache
def admin_edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        # Update product main details
        product.category_id = request.POST.get("category")
        product.name = request.POST.get("name")
        product.description = request.POST.get("description")
        product.watering = request.POST.get("watering")
        product.light_requirement = request.POST.get("light_requirement")
        product.is_active = request.POST.get("is_active") == "on"
        product.save()

        variant_ids = request.POST.getlist("variant_id[]")
        variant_types = request.POST.getlist("variant_type[]")
        prices = request.POST.getlist("price[]")
        stocks = request.POST.getlist("stock[]")

        submitted_variant_ids = set()
        existing_variants = {str(v.id): v for v in ProductVariant.objects.filter(product=product)}

        for idx, vt in enumerate(variant_types):
            price = prices[idx] if idx < len(prices) else None
            stock = stocks[idx] if idx < len(stocks) else 0
            vid = variant_ids[idx] if idx < len(variant_ids) else None

            if not vt or not price:
                continue

            # Existing or new variant
            if vid and vid in existing_variants:
                variant = existing_variants[vid]
                variant.variant_type = vt
                variant.price = price
                variant.stock = stock
                variant.save()
                submitted_variant_ids.add(vid)
            else:
                variant = ProductVariant.objects.create(
                    product=product,
                    variant_type=vt,
                    price=price,
                    stock=stock
                )

            # Handle images
            existing_image_ids = request.POST.getlist(f"existing_variant_images_{idx}[]")
            existing_images = list(variant.images.all().order_by("id"))

            for i in range(3):
                # 1. Cropped image from base64 hidden input
                cropped_img = request.POST.get(f"variant_{idx}_cropped_{i}")
                if cropped_img and ";base64," in cropped_img:
                    format, imgstr = cropped_img.split(";base64,")
                    ext = format.split("/")[-1]
                    img_data = ContentFile(base64.b64decode(imgstr), name=f"variant_{variant.id}_{i}.{ext}")

                    if i < len(existing_images):
                        existing_images[i].image.save(img_data.name, img_data, save=True)
                    else:
                        VariantImage.objects.create(variant=variant, image=img_data)
                    continue

                # 2. Uploaded image file
                file_field = f"variant_images_{idx}_{i}"
                if file_field in request.FILES:
                    if i < len(existing_images):
                        existing_images[i].image.save(request.FILES[file_field].name, request.FILES[file_field], save=True)
                    else:
                        VariantImage.objects.create(variant=variant, image=request.FILES[file_field])
                    continue

                # 3. Remove or keep existing images
                if i < len(existing_images):
                    img = existing_images[i]
                    if str(img.id) not in existing_image_ids:
                        img.delete()

        # Delete removed variants
        for vid, variant in existing_variants.items():
            if vid not in submitted_variant_ids:
                variant.delete()

        messages.success(request, "✅ Product updated successfully")
        return redirect("admin_product_list")

    # GET — load data for form
    categories = Category.objects.all()
    variants = ProductVariant.objects.filter(product=product).prefetch_related("images")

    for variant in variants:
        variant.ordered_images = list(variant.images.all().order_by("id"))

    return render(request, "admin/edit_product.html", {
        "categories": categories,
        "product": product,
        "variants": variants,
    })
#Soft Delete Product
@admin_required
@never_cache
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save()
    return redirect("admin_product_list")

# -------------------------------------CATEGORY SECTION ---------------------------


@admin_required
@never_cache
def manage_categories(request, pk=None):
    
    category_to_edit = None
    if pk:
        category_to_edit = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        category_name = request.POST.get("category_name", "").strip()

        if not category_name:
            messages.error(request, "Category name cannot be empty!")
        else:
            # Editing existing category
            if category_to_edit:  
                if Category.objects.filter(name__icontains=category_name).exclude(pk=category_to_edit.pk).exists():
                    messages.error(request, "Category already exists!")
                else:
                    category_to_edit.name = category_name
                    category_to_edit.save()
                    messages.success(request, "Category updated successfully!")
                    return redirect("manage_categories")
            else:  # Adding new category
                if Category.objects.filter(name__icontains=category_name).exists():
                    messages.error(request, "Category already exists!")
                else:
                    
                    if not re.match(r'^[A-Za-z ]+$', category_name):
                        messages.error(request,"Name should only contain letters and spaces.")
                        return redirect("manage_categories")
                    if len(category_name)<3:
                        messages.error(request,"Name length must be at least Three.")
                        return redirect("manage_categories")
                                
                        
                    Category.objects.create(name=category_name,is_active=True)
                    messages.success(request, "Category added successfully!")
                    return redirect("manage_categories")

    categories = Category.objects.all()
    return render(
        request,
        "admin/manage_categories.html",
        {
            "categories": categories,
            "category_to_edit": category_to_edit,  
        },
    )

@admin_required
@never_cache
def toggle_category_status(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_active = not category.is_active
    category.save()
    if category.is_active:
        messages.success(request, f"Category '{category.name}' unblocked successfully!")
    else:
        messages.success(request, f"Category '{category.name}' blocked successfully!")
    return redirect("manage_categories")
