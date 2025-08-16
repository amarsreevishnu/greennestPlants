from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Category, Product, ProductVariant, ProductImage



def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_superuser)(view_func)



# 📂 Category List
@admin_required
def admin_category_list(request):
    categories = Category.objects.all()
    return render(request, "custom_admin/category_list.html", {"categories": categories})


# ➕ Add Category
@admin_required
def admin_add_category(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            Category.objects.create(name=name)
        return redirect("admin_category_list")
    return render(request, "custom_admin/add_category.html")


# 📦 Product List
@admin_required
def admin_product_list(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "product/product_list.html", {"products": products})


# ➕ Add Product (manual POST handling)
@admin_required
def admin_add_product(request):
    if request.method == "POST":
        # Main product data
        category_id = request.POST.get("category")
        name = request.POST.get("name")
        description = request.POST.get("description")
        size = request.POST.get("size")
        light_requirement = request.POST.get("light_requirement")
        price = request.POST.get("price")
        main_image = request.FILES.get("main_image")
        is_active = request.POST.get("is_active") == "on"

        category = get_object_or_404(Category, id=category_id)
        product = Product.objects.create(
            category=category,
            name=name,
            description=description,
            size=size,
            light_requirement=light_requirement,
            price=price,
            main_image=main_image,
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
    return render(request, "product/add_product.html", {"categories": categories})


# ✏ Edit Product
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
    return render(request, "custom_admin/edit_product.html", {
        "categories": categories,
        "product": product,
        "variants": variants,
        "images": images
    })


# 🗑 Soft Delete Product
@admin_required
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = False
    product.save()
    return redirect("admin_product_list")
