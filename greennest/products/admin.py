from django.contrib import admin
from .models import Category, Product, ProductVariant, VariantImage

# Category
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


# Inline for Variant Images
class VariantImageInline(admin.TabularInline):
    model = VariantImage
    extra = 1


# Product Variant
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    inlines = [VariantImageInline]
    show_change_link = True


# Product
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active","watering", "created_at")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("name", "description")
    inlines = [ProductVariantInline]


# Product Variant
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "variant_type", "price", "stock", "is_active")
    list_filter = ("variant_type", "product__category")
    search_fields = ("product__name",)


# Product Variant Image
@admin.register(VariantImage)
class ProductVariantImageAdmin(admin.ModelAdmin):
    list_display = ("variant", "image")
