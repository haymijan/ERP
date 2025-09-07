# products/forms.py (সম্পূর্ণ নতুন এবং চূড়ান্ত ফাইল)

from django import forms
from .models import Product, Category, UnitOfMeasureCategory, UnitOfMeasure, Brand

# Product মডেলের জন্য ফর্ম
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'product_code', 'brand', 'category', 'tracking_method', 'description', 
            'price', 'cost_price', 'sale_price', 'min_stock_level', 'image', 'unit_of_measure', 
            'purchase_unit_of_measure', 'sale_unit_of_measure'
        ]
        labels = {
            'name': 'Product Name', 'product_code': 'Product Code/SKU', 
            'brand': 'Brand',
            'category': 'Category',
            'tracking_method': 'Tracking Method',
            'description': 'Description', 
            'price': 'Default Purchase Price',
            'cost_price': 'Cost Price',
            'sale_price': 'Sale Price',
            'min_stock_level': 'Minimum Stock Level', 'image': 'Product Image',
            'unit_of_measure': 'Default Unit of Measure',
            'purchase_unit_of_measure': 'Purchase Unit of Measure',
            'sale_unit_of_measure': 'Sale Unit of Measure',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'product_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter unique product code or SKU'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'tracking_method': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'min_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'unit_of_measure': forms.Select(attrs={'class': 'form-control'}),
            'purchase_unit_of_measure': forms.Select(attrs={'class': 'form-control'}),
            'sale_unit_of_measure': forms.Select(attrs={'class': 'form-control'}),
        }

# Category মডেলের জন্য ফর্ম (অপরিবর্তিত)
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        labels = {'name': 'Category Name'}
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'})}

# UnitOfMeasureCategory মডেলের জন্য ফর্ম (অপরিবর্তিত)
class UnitOfMeasureCategoryForm(forms.ModelForm):
    class Meta:
        model = UnitOfMeasureCategory
        fields = ['name']
        labels = {'name': 'Category Name'}
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter UoM category name (e.g., Units, Weight)'})}

# UnitOfMeasure মডেলের জন্য ফর্ম (আপনার পুরোনো কোড অনুযায়ী সংশোধিত)
class UnitOfMeasureForm(forms.ModelForm):
    class Meta:
        model = UnitOfMeasure
        fields = ['name', 'short_code', 'category', 'ratio', 'is_base_unit']
        labels = {
            'name': 'Unit Name', 'short_code': 'Short Code', 'category': 'Category',
            'ratio': 'Ratio to Base Unit', 'is_base_unit': 'Is Base Unit?'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Piece, Box, Kg'}),
            'short_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., pc, box, kg'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'ratio': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_base_unit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

#নতুন BrandForm ক্লাসটি এখানে যোগ করা হলো ---
class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name']
        labels = {'name': 'Brand Name'}
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter brand name'})}

# --- ফাইলের শেষে এই নতুন ক্লাসটি যোগ করুন ---
class ProductImportForm(forms.Form):
    file = forms.FileField(
        label="Select a CSV or Excel file",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel'})
    )