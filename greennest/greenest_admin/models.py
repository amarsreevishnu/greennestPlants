from django.db import models
from cloudinary.models import CloudinaryField

# Create your models here.

class Banner(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True)
    subtitle = models.TextField(blank=True, null=True)
    image = CloudinaryField('banners', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title if self.title else f"Banner {self.id}"
