from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Category, Product, ProductVariant, ProductImage
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
import base64



def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_superuser,login_url='/greenneest_admin/login/')(view_func)



# Category List
@admin_required
def admin_category_list(request):
    categories = Category.objects.all()
    return render(request, "admin/category_list.html", {"categories": categories})


# Add Category
@admin_required
def admin_add_category(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            Category.objects.create(name=name)
        return redirect("admin_category_list")
    return render(request, "admin/add_category.html")


def process_image(image_file, max_size=(800, 800), quality=75):
    """Resize & compress image before saving."""
    img = Image.open(image_file)

    # Convert transparency (PNG) to RGB
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize (maintain aspect ratio)
    img.thumbnail(max_size)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)

    return ContentFile(buffer.getvalue(), name=image_file.name if hasattr(image_file, 'name') else "image.jpg")


# Product List
@admin_required
def admin_product_list(request):
    products = Product.objects.all().order_by('-id')  # latest first
    
    paginator = Paginator(products, 10)# Pagination: 10 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/product_list.html', {'products': page_obj })
    


#  Add Product (manual POST handling)
@admin_required
def admin_add_product(request):
    if request.method == "POST":
        
        category_id = request.POST.get("category")
        name = request.POST.get("name")
        description = request.POST.get("description")
        size = request.POST.get("size")
        light_requirement = request.POST.get("light_requirement")
        price = request.POST.get("price")
        
        stock = request.POST.get("stock") or 0  
        is_active = request.POST.get("is_active") == "on"
        cropped_image = request.POST.get("main_image")
        if cropped_image:  # If hidden field has base64 image
            format, imgstr = cropped_image.split(";base64,")
            ext = format.split("/")[-1]  # get jpg, png etc.
            image_file = ContentFile(base64.b64decode(imgstr), name=f"cropped.{ext}")
            
        else:
            # Fallback: normal file input
            image_file = request.FILES.get("main_image")

        category = get_object_or_404(Category, id=category_id)
        product = Product.objects.create(
            category=category,
            name=name,
            description=description,
            size=size,
            light_requirement=light_requirement,
            price=price,
            main_image=image_file,
            stock=stock,
            is_active=is_active
        )

        # Variants
        growth_stages = request.POST.getlist("growth_stage[]")
        additional_prices = request.POST.getlist("additional_price[]")
        for stage, add_price in zip(growth_stages, additional_prices):
            if stage:
                ProductVariant.objects.create(
                    product=product,
                    growth_stage=stage,
                    additional_price=add_price or 0
                )

        # Additional Images
        for img in request.FILES.getlist("extra_images"):
            ProductImage.objects.create(product=product, image=img)

        return redirect("admin_product_list")

    categories = Category.objects.all()
    return render(request, "admin/add_product.html", {"categories": categories})


# Edit Product
@admin_required
def admin_edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        # Update product
        product.category_id = request.POST.get("category")
        product.name = request.POST.get("name")
        product.description = request.POST.get("description")
        product.size = request.POST.get("size")
        product.light_requirement = request.POST.get("light_requirement")
        product.price = request.POST.get("price")
        if request.FILES.get("main_image"):
            product.main_image = request.FILES.get("main_image")
        product.stock = request.POST.get("stock") or product.stock
        product.is_active = request.POST.get("is_active") == "on"
        product.save()

        # Clear old variants & re-add
        ProductVariant.objects.filter(product=product).delete()
        growth_stages = request.POST.getlist("growth_stage[]")
        additional_prices = request.POST.getlist("additional_price[]")
        for stage, add_price in zip(growth_stages, additional_prices):
            if stage:
                ProductVariant.objects.create(
                    product=product,
                    growth_stage=stage,
                    additional_price=add_price or 0
                )

        # Add new additional images
        for img in request.FILES.getlist("extra_images"):
            ProductImage.objects.create(product=product, image=img)

        return redirect("admin_product_list")

    categories = Category.objects.all()
    variants = ProductVariant.objects.filter(product=product)
    images = ProductImage.objects.filter(product=product)
    return render(request, "admin/edit_product.html", {
        "categories": categories,
        "product": product,
        "variants": variants,
        "images": images
    })


# Soft Delete Product
@admin_required
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active 
    product.save()
    return redirect("admin_product_list")


# Product List for Users

def user_product_list(request):
    # Fetch only active products
    products = Product.objects.filter(is_active=True, stock__gt=0)
    return render(request, "admin/user_product_list.html", {"products": products})