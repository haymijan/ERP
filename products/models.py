# products/models.py

from django.db import models
from io import BytesIO
from django.core.files import File
import barcode
from barcode.writer import ImageWriter
from django.db.models import Sum # এটি স্টক স্ট্যাটাস আপডেটের জন্য প্রয়োজন
from django.core.exceptions import ValidationError # Custom validation এর জন্য (যদি আপনি clean মেথড ব্যবহার করেন)
from django.utils.translation import gettext_lazy as _ # Custom validation এর জন্য (যদি আপনি clean মেথড ব্যবহার করেন)
from django.utils.html import format_html

class Brand(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'inventory_brand'
        ordering = ['name']

class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'inventory_category'
        verbose_name_plural = "Categories"

class UnitOfMeasureCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'inventory_unitofmeasurecategory'
        verbose_name_plural = "Unit of Measure Categories"

class UnitOfMeasure(models.Model):
    name = models.CharField(max_length=100, unique=True)
    short_code = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Short code for the unit (e.g., 'pc' for piece)")
    category = models.ForeignKey(UnitOfMeasureCategory, on_delete=models.CASCADE)
    ratio = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    rounding = models.DecimalField(max_digits=10, decimal_places=4, default=0.001)
    is_base_unit = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.short_code:
            return f"{self.name} ({self.short_code})"
        return self.name

    class Meta:
        db_table = 'inventory_unitofmeasure'

class Product(models.Model):
    # --- সমস্ত ফিল্ড এখন একসাথে এবং সঠিক ক্রমে আছে ---
    TRACKING_CHOICES = [
        ('none', 'Not Tracked'),
        ('lot', 'By Lots/Batches'),
        ('serial', 'By Serial Numbers'),
    ]
    tracking_method = models.CharField(max_length=10, choices=TRACKING_CHOICES, default='none', verbose_name="Tracking Method")
    
    product_code = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Product Code/SKU")
    
    name = models.CharField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='products_supplied')
    description = models.TextField(blank=True, null=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Default Purchase Price")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # --- cost_price ফিল্ডটিকে এখানে, সঠিক জায়গায় আনা হয়েছে ---
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="The actual cost of acquiring the product."
    )
    
    min_stock_level = models.PositiveIntegerField(default=5)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    barcode = models.ImageField(upload_to='barcodes/', blank=True, null=True, verbose_name="Barcode Image")

    unit_of_measure = models.ForeignKey(UnitOfMeasure, on_delete=models.SET_NULL, null=True, blank=True, related_name='products_by_uom')
    purchase_unit_of_measure = models.ForeignKey(UnitOfMeasure, on_delete=models.SET_NULL, null=True, blank=True, related_name='products_by_purchase_uom')
    sale_unit_of_measure = models.ForeignKey(UnitOfMeasure, on_delete=models.SET_NULL, null=True, blank=True, related_name='products_by_sale_uom')
    
    STATUS_CHOICES = [('in_stock', 'In Stock'), ('low_stock', 'Low Stock'), ('out_of_stock', 'Out of Stock')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='out_of_stock')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # total_quantity প্রপার্টি যোগ করা হয়েছে
    @property
    def total_quantity(self):
        # এই প্রপার্টিটি Stock মডেলের সাথে সম্পর্কিত, তাই এটি stock.models থেকে Stock ইম্পোর্ট করা আবশ্যক।
        from stock.models import Stock # এখানে ইম্পোর্ট করা হয়েছে যাতে circular import এড়ানো যায়
        return Stock.objects.filter(product=self).aggregate(total=Sum('quantity'))['total'] or 0

    # barcode_image_tag প্রপার্টি যোগ করা হয়েছে
    @property
    def barcode_image_tag(self):
        if self.barcode and hasattr(self.barcode, 'url'):
            return format_html('<img src="{}" height="50px" />', self.barcode.url)
        return "No Barcode"

    def __str__(self): # __str__ মেথড Product এর নাম এবং কোড রিটার্ন করবে
        if self.product_code:
            return f"{self.name} ({self.product_code})"
        return self.name

    def save(self, *args, **kwargs):
        # বারকোড তৈরির লজিক: যদি barcode ফিল্ড খালি থাকে এবং product_code থাকে
        if not self.barcode and self.product_code:
            try:
                Code128 = barcode.get_barcode_class('code128')
                code = Code128(self.product_code, writer=ImageWriter())
                buffer = BytesIO()
                code.write(buffer)
                self.barcode.save(f'{self.product_code}.png', File(buffer), save=False)
            except Exception as e:
                print(f"Error generating barcode for {self.product_code}: {e}")
                # আপনি চাইলে এখানে একটি error message যোগ করতে পারেন বা log করতে পারেন।

        # স্টক স্ট্যাটাস আপডেট করার লজিকটি এখন সিগনাল দ্বারা পরিচালিত হবে।
        # তাই এটি save() মেথড থেকে সরানো হয়েছে।
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'inventory_product'
        verbose_name_plural = "Products"
