from django.urls import path
from . import views

app_name = 'costing'

urlpatterns = [
    path('report/', views.job_costing_report, name='job_costing_report'),
    path('report/export/pdf/', views.export_job_costing_pdf, name='export_job_costing_pdf'),
]