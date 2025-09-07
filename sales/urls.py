# sales/urls.py (সংশোধিত সম্পূর্ণ ফাইল)

from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.sales_order_list, name='sales_order_list'),
    path('create/', views.create_sales_order, name='create_sales_order'),
    path('<int:pk>/', views.sales_order_detail, name='sales_order_detail'),
    path('<int:pk>/edit/', views.edit_sales_order, name='edit_sales_order'),
    path('<int:pk>/delete/', views.delete_sales_order, name='delete_sales_order'),
    path('<int:pk>/fulfill/', views.fulfill_sales_order, name='fulfill_sales_order'),
    path('get-product-sale-price/', views.get_product_sale_price_ajax, name='get_product_sale_price'),
    path('get-lots/', views.get_lots_by_location_and_product, name='get_lots_by_location_and_product'),
    path('export/pdf/<int:pk>/', views.export_sales_order_pdf, name='export_sales_order_pdf'),
    path('returns/create/', views.create_sales_return, name='create_sales_return'),
]