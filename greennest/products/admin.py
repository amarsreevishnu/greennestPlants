from django.contrib import admin
from .models import Category, Product, ProductVariant, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "size", "light_requirement", "price", "is_active")
    list_filter = ("category", "size", "light_requirement", "is_active")
    search_fields = ("name",)
    inlines = [ProductVariantInline, ProductImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)


admin.site.register(ProductVariant)
admin.site.register(ProductImage)
