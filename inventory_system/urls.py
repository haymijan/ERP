# inventory_system/urls.py (সংশোধিত ফাইল)

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from .views import dashboard, home


from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('django.contrib.auth.urls')), #Password Reset URLs
    path('', dashboard, name='dashboard'), 
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('', views.home, name='home'),

    path('products/', include('products.urls', namespace='products')),
    path('partners/', include('partners.urls', namespace='partners')), # <-- ডুপ্লিকেট লাইনটি মুছে ফেলা হয়েছে
    path('sales/', include('sales.urls', namespace='sales')),
    path('purchases/', include('purchase.urls', namespace='purchase')),
    path('stock/', include('stock.urls', namespace='stock')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('pos/', include('pos.urls', namespace='pos')),
    path('management/', include(('management.urls', 'management'), namespace='management')),
    path('costing/', include('costing.urls', namespace='costing')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)