from django.db import models
from django.contrib.auth.models import AbstractUser
from stock.models import Warehouse # <-- Warehouse মডেল ইম্পোর্ট করা হলো

class User(AbstractUser):
    """
    Custom User model to extend Django's default User.
    This allows adding custom fields like 'warehouse' directly to the User.
    """
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users', # এই গুদামের সাথে যুক্ত ইউজারদের সহজে খুঁজে পাওয়ার জন্য
        verbose_name="Assigned Warehouse" # অ্যাডমিন প্যানেলে প্রদর্শনের জন্য
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username