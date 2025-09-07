# reports/urls.py
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('daily-sales-report/', views.daily_sales_report, name='daily_sales_report'),
    path('expiry-report/', views.expiry_report_view, name='expiry_report'),
    path('dead-stock-report/', views.dead_stock_report_view, name='dead_stock_report'),
    path('purchase-suggestion-report/', views.purchase_suggestion_report_view, name='purchase_suggestion_report'),
    
    # --- নতুন এবং উন্নত URL ---
    path('daily-sales-report/export/excel/', views.export_daily_sales_excel, name='export_daily_sales_excel'),
    path('daily-sales-report/export/pdf/', views.export_daily_sales_pdf, name='export_daily_sales_pdf'), # <-- নতুন PDF URL
]