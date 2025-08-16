from django.db import models

# Create your models here.

# Category Model
class Category(models.Model):
    CATEGORY_CHOICES = [
        ("Indoor", "Indoor"),
        ("Outdoor", "Outdoor"),
    ]
    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)

    def __str__(self):
        return self.name

# Product Model
class Product(models.Model):
    SIZE_CHOICES = [
        ("S", "Small"),
        ("M", "Medium"),
        ("L", "Large"),
    ]
    LIGHT_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("Bright", "Bright"),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    size = models.CharField(max_length=1, choices=SIZE_CHOICES)
    light_requirement = models.CharField(max_length=10, choices=LIGHT_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    main_image = models.ImageField(upload_to="plants/main/")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.category.name})"


# Product Variant (Plant Growth )
class ProductVariant(models.Model):
    GROWTH_CHOICES = [
        ("Seedling", "Seedling"),
        ("Young", "Young"),
        ("Mature", "Mature"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    growth_stage = models.CharField(max_length=20, choices=GROWTH_CHOICES)
    additional_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.growth_stage} - {self.product.name}"


# Additional Images
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="plants/gallery/")

    def __str__(self):
        return f"Extra Image for {self.product.name}"
