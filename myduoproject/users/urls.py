from django.urls import path
from . import views
# Import views จาก Django Auth เพื่อใช้ในการ Login (standard Django view)
from django.contrib.auth import views as auth_views

app_name = 'users'

urlpatterns = [
    # 1. Register: /users/register/
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # 2. Login: /users/login/ (ใช้ Django Built-in View และชี้ไปที่ template ที่เราสร้าง)
    path('login/', 
         auth_views.LoginView.as_view(template_name='users/login.html'), 
         name='login'),
         
    # 3. Logout: /users/logout/
    path('logout/', views.user_logout, name='logout'),
    
    # 4. Profile: /users/profile/ (ต้อง Login ก่อน)
    path('profile/', views.ProfileView.as_view(), name='profile'),
]