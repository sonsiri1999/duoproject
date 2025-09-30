from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    User Admin class ที่กำหนดเอง เพื่อแสดงฟิลด์เพิ่มเติมใน CustomUser
    """
    # 1. ขยายฟิลด์ที่แสดงในหน้า list
    list_display = UserAdmin.list_display + ('phone_number', 'is_staff')
    
    # 2. ปรับโครงสร้าง Fieldsets ในหน้า Edit
    fieldsets = UserAdmin.fieldsets + (
        ('ข้อมูลติดต่อและการจัดส่ง', {
            'fields': ('phone_number', 'shipping_address', 'date_of_birth'),
        }),
    )
    
    # 3. เพิ่มฟิลด์ใหม่ในฟอร์มสำหรับการสร้าง User ใหม่
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('ข้อมูลติดต่อและการจัดส่ง', {
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'shipping_address'),
        }),
    )
