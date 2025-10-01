from django.urls import path
from . import views

# *** บรรทัดนี้สำคัญที่สุดสำหรับการใช้ orders:cart ***
app_name = 'orders' 

urlpatterns = [
    # Cart Summary
    # ย้อนกลับไปใช้ name='cart' เพื่อให้เข้ากับ Template และจุดอื่นๆ
    path('cart/', views.CartSummaryView.as_view(), name='cart'), # <-- name='cart'
    
    # Cart Management (ใช้ AJAX)
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    
    # Promotions
    path('promotion/apply/', views.apply_promotion, name='apply_promotion'),
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),
    
    # Checkout and Order Detail
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('order/<str:order_number>/', views.OrderDetailView.as_view(), name='order_detail'),
]
