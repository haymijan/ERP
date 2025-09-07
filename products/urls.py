from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [

    # Sample Template Download
    path('import/sample-template/', views.download_sample_template, name='download_sample_template'),

    # Bulk Import
    path('import/', views.import_products_view, name='import_products'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:pk>/delete/', views.delete_product, name='delete_product'),
    path('products/export/excel/', views.export_products_excel, name='export_products_excel'),
    path('products/export/pdf/', views.export_products_pdf, name='export_products_pdf'),
    path('products/print-labels/', views.print_product_labels, name='print_product_labels'),
    path('products/bulk-action/', views.product_bulk_action, name='product_bulk_action'),
    path('ajax/get-product-price/', views.get_product_sale_price, name='get_product_sale_price'),
    path('stock/<int:pk>/', views.product_stock_by_location, name='product_stock_by_location'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/<int:pk>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),

    # UoM Categories
    path('uom/categories/', views.uom_category_list, name='uom_category_list'),
    path('uom/categories/add/', views.add_uom_category, name='add_uom_category'),
    path('uom/categories/<int:pk>/edit/', views.edit_uom_category, name='edit_uom_category'),
    path('uom/categories/<int:pk>/delete/', views.delete_uom_category, name='delete_uom_category'),

    # UoM
    path('uom/', views.unit_of_measure_list, name='unit_of_measure_list'),
    path('uom/add/', views.add_unit_of_measure, name='add_unit_of_measure'),
    path('uom/<int:pk>/edit/', views.edit_unit_of_measure, name='edit_unit_of_measure'),
    path('uom/<int:pk>/delete/', views.delete_unit_of_measure, name='delete_unit_of_measure'),
    # ... (edit and delete urls for UoM will be added next)

    # Brands
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/add/', views.add_brand, name='add_brand'),
    path('brands/<int:pk>/edit/', views.edit_brand, name='edit_brand'),
    path('brands/<int:pk>/delete/', views.delete_brand, name='delete_brand'),

]