# products/admin.py (চূড়ান্ত সংশোধিত এবং নির্ভুল সংস্করণ)

from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import Category, UnitOfMeasureCategory, UnitOfMeasure, Product, Brand
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce

# --- Brand, Category, UoM ইত্যাদি অপরিবর্তিত থাকবে ---
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(UnitOfMeasureCategory)
class UnitOfMeasureCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    def get_short_code(self, obj):
        return obj.short_code
    get_short_code.short_description = 'Short Code'
    list_display = ('name', 'get_short_code', 'category', 'ratio', 'is_base_unit')
    list_filter = ('category', 'is_base_unit')
    search_fields = ('name', 'short_code')


# --- Product Resource (ইম্পোর্ট-এক্সপোর্টের জন্য) ---
class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        fields = ('id', 'name', 'product_code', 'category__name', 'brand__name', 'price', 'sale_price', 'cost_price', 'min_stock_level', 'tracking_method', 'is_active')
        export_order = fields

# --- চূড়ান্ত ProductAdmin ক্লাস ---
@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource

    def real_time_status(self, obj):
        # --- মূল পরিবর্তন: NoneType error প্রতিরোধের জন্য ---
        quantity = obj._total_quantity if hasattr(obj, '_total_quantity') and obj._total_quantity is not None else 0
        min_stock = obj.min_stock_level if obj.min_stock_level is not None else 0
        # --- পরিবর্তন শেষ ---

        if quantity > min_stock:
            return format_html('<span style="color: green; font-weight: bold;">In Stock</span>')
        elif 0 < quantity <= min_stock:
            return format_html('<span style="color: orange; font-weight: bold;">Low Stock</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">Out of Stock</span>')
    real_time_status.short_description = 'Status'
    real_time_status.admin_order_field = '_total_quantity'

    def get_total_quantity(self, obj):
        return obj._total_quantity if hasattr(obj, '_total_quantity') and obj._total_quantity is not None else 0
    get_total_quantity.short_description = 'Quantity'

    def get_barcode_image_tag(self, obj):
        return obj.barcode_image_tag
    get_barcode_image_tag.short_description = 'Barcode'

    list_display = ('name', 'product_code', 'brand', 'category', 'price', 'sale_price', 'get_total_quantity', 'real_time_status')
    list_filter = ('category', 'brand', 'tracking_method')
    search_fields = ('name', 'product_code', 'brand__name', 'description')
    
    readonly_fields = ('get_total_quantity', 'get_barcode_image_tag')
    fieldsets = (
        (None, {'fields': ('name', 'product_code', 'category', 'description', 'image')}),
        ('Pricing & Stock', {'fields': ('price', 'cost_price', 'sale_price', 'min_stock_level', 'tracking_method')}),
        ('Units of Measure', {'fields': ('unit_of_measure', 'purchase_unit_of_measure', 'sale_unit_of_measure')}),
        ('Barcode', {'fields': ('barcode', 'get_barcode_image_tag')}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # --- Coalesce যোগ করা হয়েছে None মানকে ০ তে রূপান্তর করার জন্য ---
        queryset = queryset.annotate(_total_quantity=Coalesce(Sum('stocks__quantity'), Value(0)))
        return queryset