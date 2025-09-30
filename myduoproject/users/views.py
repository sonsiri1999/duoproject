from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import View
from django.utils.decorators import method_decorator

# FIX: เปลี่ยน UserRegisterForm เป็น CustomUserCreationForm
from .forms import CustomUserCreationForm, UserUpdateForm 
from orders.models import Order # ใช้สำหรับดึงประวัติการสั่งซื้อ

# ----------------------------------------------------------------------
# Registration View (Class-based View)
# ----------------------------------------------------------------------
class RegisterView(View):
    """Handles user registration."""
    template_name = 'users/register.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('products:product_list')
        form = CustomUserCreationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in immediately after registration
            login(request, user)
            messages.success(request, f"ยินดีต้อนรับ! บัญชี {user.username} ถูกสร้างสำเร็จแล้ว.")
            return redirect('products:product_list')
        
        return render(request, self.template_name, {'form': form})

# ----------------------------------------------------------------------
# Logout View (Simple Function)
# ----------------------------------------------------------------------
def user_logout(request):
    """Logs the current user out."""
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "คุณออกจากระบบเรียบร้อยแล้ว.")
    return redirect('products:product_list')

# ----------------------------------------------------------------------
# Profile and Update View (Login Required)
# ----------------------------------------------------------------------
# แก้ไข login_url เป็น 'users:login' เพื่อให้ตรงกับ namespace
@method_decorator(login_required(login_url='users:login'), name='dispatch')
class ProfileView(View):
    """Displays user profile and handles updates."""
    template_name = 'users/profile.html'
    
    def get(self, request):
        # ดึงประวัติการสั่งซื้อ
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        
        profile_form = UserUpdateForm(instance=request.user)
        
        context = {
            'profile_form': profile_form,
            'orders': orders,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # ใช้ instance=request.user เพื่อโหลดข้อมูลเดิม
        profile_form = UserUpdateForm(request.POST, instance=request.user)
        
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "ข้อมูลโปรไฟล์ถูกบันทึกเรียบร้อยแล้ว!")
            return redirect('profile') 

        # หากฟอร์มไม่ถูกต้อง ให้กลับไปที่หน้าเดิมพร้อมข้อผิดพลาด
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        context = {
            'profile_form': profile_form,
            'orders': orders,
        }
        messages.error(request, "เกิดข้อผิดพลาดในการบันทึกข้อมูล กรุณาตรวจสอบอีกครั้ง.")
        return render(request, self.template_name, context)
