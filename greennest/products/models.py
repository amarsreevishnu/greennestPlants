from django.db import models


# Category Model (dynamic)
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True,null=False, blank=False)
    is_active = models.BooleanField(default=True) 
    

    def __str__(self):
        return self.name


# Product Model
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    watering = models.TextField( null=True, blank=True)
    light_requirement = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.name} ({self.category.name})"


# Product Variant (dynamic type + price + stock)
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    variant_type = models.CharField(max_length=100, null=False, blank=False) 
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.variant_type} (₹{self.price}, Stock: {self.stock})"

    def main_image(self):
        """Return first image of the variant as main image"""
        return self.images.first()
    
   
    #  for every where --best offer info
    @property
    def best_offer_info(self):
        from offer.utils import get_best_offer
        return get_best_offer(self)

    @property
    def discounted_price(self):
        return self.best_offer_info["final_price"]

    @property
    def discount_percent(self):
        return self.best_offer_info["discount"]

    @property
    def offer_type(self):
        return self.best_offer_info["offer_type"]

    


# Variant Images (up to 3 images per variant)
class VariantImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/variants/")

    def __str__(self):
        return f"Image for {self.variant.product.name} - {self.variant.variant_type}"
