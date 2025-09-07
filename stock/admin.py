from django.contrib import admin
from .models import Warehouse, Location, Stock, LotSerialNumber, InventoryTransaction

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'created_at')
    search_fields = ('name',)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'warehouse', 'parent_location')
    list_filter = ('warehouse',)
    search_fields = ('name', 'warehouse__name')

@admin.register(Stock) # ProductStockAdmin এর পরিবর্তে StockAdmin
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'updated_at')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'warehouse__name')

@admin.register(LotSerialNumber)
class LotSerialNumberAdmin(admin.ModelAdmin):
    list_display = ('product', 'lot_number', 'location', 'quantity', 'expiration_date')
    list_filter = ('location__warehouse', 'product')
    search_fields = ('lot_number', 'product__name')

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'product', 'transaction_type', 'quantity', 'user')
    list_filter = ('transaction_type', 'transaction_date', 'user')
    search_fields = ('product__name', 'notes')