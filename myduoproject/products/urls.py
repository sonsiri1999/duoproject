from django.urls import path
from . import views

# กำหนดชื่อแอปพลิเคชัน
app_name = 'products' 

urlpatterns = [
    # 1. Product List (Home Page for Products)
    # ใช้ ProductListView.as_view()
    path('', views.ProductListView.as_view(), name='product_list'), 
    
    # 2. Product Detail (แก้ไข NoReverseMatch: 'product_detail')
    # ต้องใช้ <str:slug>/ เพื่อให้ตรงกับ get_object ใน ProductDetailView
    path('<str:slug>/', views.ProductDetailView.as_view(), name='product_detail'), 
    
    # 3. Cart Interaction (AJAX POST)
    path('api/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    
    # 4. Staff/Admin View (สำหรับเพิ่มสินค้า)
    path('staff/create/', views.ProductCreateView.as_view(), name='product_create'),
]