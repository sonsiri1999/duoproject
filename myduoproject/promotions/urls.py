from django.urls import path
from . import views

# กำหนด URL Patterns ที่จะใช้สำหรับ App promotions
# ปัจจุบันยังไม่มี View ที่เกี่ยวข้องกับการแสดงผล
urlpatterns = [
    path('apply/', views.apply_promotion, name='apply_promotion'), 
]
