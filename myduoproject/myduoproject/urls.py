from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views 
from django.views.generic.base import TemplateView

from products.views import ProductListView

urlpatterns = [
    # 1. Django Admin (ระบบผู้ดูแล)
    path('admin/', admin.site.urls),
    path('', ProductListView.as_view(), name='home'),
    
    # 2. Authentication: Logout (ใช้ชื่อ 'logout' ตรงตามที่ template ต้องการ)
    # เมื่อผู้ใช้ออกจากระบบ จะนำทางไปยังหน้าแรก ('/')
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/', include('allauth.urls')),
    path('', ProductListView.as_view(), name='home'),
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),
    path('', include('products.urls', namespace='products')), 
    
    path('orders/', include('orders.urls', namespace='orders')), 
    # path('', TemplateView.as_view(template_name='base.html'), name='home'),
    path('users/', include('users.urls', namespace='users')), 
    
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# การตั้งค่า Static และ Media (ต้องมีเฉพาะใน settings.DEBUG เท่านั้น)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
