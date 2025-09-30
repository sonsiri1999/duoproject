from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views 

urlpatterns = [
    # 1. Django Admin (ระบบผู้ดูแล)
    path('admin/', admin.site.urls),
    
    # 2. Authentication: Logout (ใช้ชื่อ 'logout' ตรงตามที่ template ต้องการ)
    # เมื่อผู้ใช้ออกจากระบบ จะนำทางไปยังหน้าแรก ('/')
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    
    # 3. Main App: Products (หน้าหลัก/รายการสินค้า)
    # กำหนดให้เป็น root URL ('') และใช้ namespace 'products' (เช่น products:product_list)
    path('', include('products.urls', namespace='products')), 
    
    # 4. App: Orders (ตะกร้าสินค้า/ชำระเงิน/รายการสั่งซื้อ)
    # กำหนด prefix เป็น 'orders/' และใช้ namespace 'orders' (เช่น orders:cart)
    path('orders/', include('orders.urls', namespace='orders')), 
    
    # 5. App: Users (หน้าโปรไฟล์/จัดการบัญชี)
    # กำหนด prefix เป็น 'users/' หรือจะใช้ 'accounts/' ก็ได้ แต่เลือก 'users/' เพื่อความชัดเจน
    # ใช้ namespace 'users' (เช่น users:profile)
    path('users/', include('users.urls', namespace='users')), 
]

# การตั้งค่า Static และ Media (ต้องมีเฉพาะใน settings.DEBUG เท่านั้น)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
