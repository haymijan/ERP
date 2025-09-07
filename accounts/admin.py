# accounts/admin.py (আপনার কোডের পরিমার্জিত এবং চূড়ান্ত সংস্করণ)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom User Admin to display and filter by the 'warehouse' field.
    """
    # ব্যবহারকারী এডিট করার সময় 'warehouse' ফিল্ডটি দেখানোর জন্য
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Warehouse Information', {'fields': ('warehouse',)}),
    )
    
    # নতুন ব্যবহারকারী তৈরি করার সময় 'warehouse' ফিল্ডটি যোগ করার জন্য
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Warehouse Information', {'fields': ('warehouse',)}),
    )

    # ব্যবহারকারীর তালিকায় 'warehouse' কলামটি দেখানোর জন্য
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'warehouse')
    
    # ডানদিকের ফিল্টার অপশনে 'warehouse' যোগ করার জন্য
    list_filter = BaseUserAdmin.list_filter + ('warehouse',)

    # সার্চ করার সময় 'warehouse' নাম দিয়েও খোঁজার সুবিধা যোগ করার জন্য
    search_fields = ('username', 'email', 'first_name', 'last_name', 'warehouse__name')