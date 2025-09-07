# partners/urls.py (সম্পূর্ণ সংশোধিত ফাইল)

from django.urls import path
from . import views

app_name = 'partners'

urlpatterns = [
    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/<int:pk>/edit/', views.edit_supplier, name='edit_supplier'),
    path('suppliers/<int:pk>/delete/', views.delete_supplier, name='delete_supplier'),

    # Customer URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/<int:pk>/edit/', views.edit_customer, name='edit_customer'),
    path('customers/<int:pk>/delete/', views.delete_customer, name='delete_customer'),
    
    # AJAX URLs
    path('ajax/add-supplier/', views.ajax_add_supplier, name='ajax_add_supplier'),
    path('ajax/add-customer/', views.ajax_add_customer, name='ajax_add_customer'),
]