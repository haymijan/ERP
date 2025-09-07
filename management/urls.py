
from django.urls import path
from . import views

app_name = 'management'

urlpatterns = [
        path('backup-restore/', views.backup_restore_view, name='backup_restore'),
        path('backup/delete/<str:filename>/', views.delete_backup_view, name='delete_backup'),

]