# partners/admin.py

from django.contrib import admin
from .models import Customer, Supplier

# Customer মডেলকে Django অ্যাডমিন প্যানেলে রেজিস্টার করা হয়েছে।
# list_display: অ্যাডমিন তালিকায় প্রদর্শিত ক্ষেত্রগুলি।
# search_fields: এই ক্ষেত্রগুলি ব্যবহার করে গ্রাহকদের অনুসন্ধান করা যাবে।
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email', 'phone')

# Supplier মডেলকে Django অ্যাডমিন প্যানেলে রেজিস্টার করা হয়েছে।
# list_display: অ্যাডমিন তালিকায় প্রদর্শিত ক্ষেত্রগুলি।
# search_fields: এই ক্ষেত্রগুলি ব্যবহার করে সরবরাহকারীদের অনুসন্ধান করা যাবে।
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email', 'phone')

