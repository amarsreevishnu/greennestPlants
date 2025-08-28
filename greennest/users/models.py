from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings




class User(AbstractUser):
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  

    def __str__(self):
        return self.email

class EmailOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now=True)  # auto update on save

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=1)


# User Profile
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=[("male", "Male"), ("female", "Female")], blank=True
    )
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"


# Multiple Addresses
class Address(models.Model):
    ADDRESS_TYPES = [
        ("home", "Home"),
        ("office", "Office"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses"
    )
    address_type = models.CharField(
        max_length=20, choices=ADDRESS_TYPES, default="home"
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20,)
    line1 = models.CharField("Address Line 1", max_length=255)
    line2 = models.CharField("Address Line 2", max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")

    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.address_type}"

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)