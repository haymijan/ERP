# pos/urls.py (নতুন ফাইল)

from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.pos_view, name='pos_view'),
    
    # কার্ট পরিচালনার জন্য AJAX URL
    path('ajax/add-to-cart/', views.pos_add_to_cart, name='pos_add_to_cart'),
    path('ajax/remove-from-cart/', views.pos_remove_from_cart, name='pos_remove_from_cart'),
    path('ajax/get-cart/', views.pos_get_cart, name='pos_get_cart'),
    
    # চেকআউট প্রক্রিয়া সম্পন্ন করার জন্য AJAX URL
    path('ajax/checkout/', views.pos_checkout_view, name='pos_checkout_view'),
    
    # রসিদ (Receipt) দেখানোর জন্য URL
    path('receipt/<int:order_id>/', views.pos_receipt_view, name='pos_receipt_view'),
]