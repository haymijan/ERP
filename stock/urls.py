# stock/urls.py

from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    # Warehouse URLs
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/add/', views.add_warehouse, name='add_warehouse'),
    path('warehouses/<int:pk>/edit/', views.edit_warehouse, name='edit_warehouse'),
    path('warehouses/<int:pk>/delete/', views.delete_warehouse, name='delete_warehouse'),

    # Location URLs
    path('locations/', views.location_list, name='location_list'),
    path('locations/add/', views.add_location, name='add_location'),
    path('locations/<int:pk>/edit/', views.edit_location, name='edit_location'),
    path('locations/<int:pk>/delete/', views.delete_location, name='delete_location'),

    # Lot/Serial URLs
    path('lots/', views.lot_serial_list, name='lot_serial_list'),
    path('lots/add/', views.add_lot_serial, name='add_lot_serial'),
    path('lots/<int:pk>/edit/', views.edit_lot_serial, name='edit_lot_serial'),
    path('lots/<int:pk>/delete/', views.delete_lot_serial, name='delete_lot_serial'),

    # Transaction URLs
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/download/', views.download_transaction_report, name='download_transaction_report'),
    path('transactions/record/', views.record_transaction, name='record_transaction'),
    path('transactions/<int:pk>/edit/', views.edit_transaction, name='edit_transaction'),
    path('transactions/<int:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    path('inventory/adjust/', views.inventory_adjustment, name='inventory_adjustment'),
    
    # Report URLs
    path('reports/stock-movement/', views.stock_movement_report, name='stock_movement_report'),
    
    # Product Stock Details URL
    path('product/<int:product_id>/details/', views.product_stock_details, name='product_stock_details'),

    # AJAX URLs
    path('ajax/check-product-tracking/<int:product_id>/', views.check_product_tracking, name='check_product_tracking'),
    path('ajax/get-available-lots/', views.get_available_lots, name='get_available_lots'),
    path('ajax/get_lots_by_location_and_product/', views.get_lots_by_location_and_product, name='get_lots_by_location_and_product'),
    
]