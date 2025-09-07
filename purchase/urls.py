# purchase/urls.py
from django.urls import path
from . import views

app_name = 'purchase'

urlpatterns = [
    path('', views.purchase_order_list, name='purchase_order_list'),
    path('create/', views.create_purchase_order, name='create_purchase_order'),
    path('<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('<int:pk>/edit/', views.edit_purchase_order, name='edit_purchase_order'),
    path('export/excel/', views.export_purchase_orders_excel, name='export_purchase_orders_excel'),
    path('export/pdf/', views.export_purchase_orders_pdf, name='export_purchase_orders_pdf'),
    path('<int:pk>/receive/', views.receive_purchase_order, name='receive_purchase_order'),
    path('<int:pk>/export/pdf/', views.export_single_purchase_order_pdf, name='export_single_purchase_order_pdf'),
    path('<int:pk>/export/receipt/pdf/', views.export_single_purchase_receipt_pdf, name='export_single_purchase_receipt_pdf'),
    
    # --- নতুন AJAX URL গুলো যোগ করা হয়েছে ---
    path('ajax/get-products-by-supplier/', views.get_products_by_supplier_ajax, name='get_products_by_supplier_ajax'),
    path('ajax/get-product-price-by-supplier/', views.get_product_price_by_supplier_ajax, name='get_product_price_by_supplier_ajax'),
    path('stock-transfer/create/', views.create_stock_transfer_request, name='create_stock_transfer_request'),
    path('stock-transfer/list/', views.stock_transfer_request_list, name='stock_transfer_request_list'),
    path('stock-transfer/<int:pk>/', views.stock_transfer_detail, name='stock_transfer_detail'), # <-- নতুন URL
    path('stock-transfer/<int:pk>/approve/', views.approve_stock_transfer, name='approve_stock_transfer'), # <-- নতুন URL
    #path('stock-transfer/<int:pk>/process/', views.process_stock_transfer, name='process_stock_transfer'),
    path('stock-transfer/<int:pk>/receive/', views.receive_stock_transfer, name='receive_stock_transfer'), # <-- নতুন URL
    path('ajax/get-lots-for-location/', views.get_lots_for_location_ajax, name='ajax_get_lots_for_location'),

]