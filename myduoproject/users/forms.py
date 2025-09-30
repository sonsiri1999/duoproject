from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

# ----------------------------------------------------------------------
# 1. Registration Form
# ----------------------------------------------------------------------

class CustomUserCreationForm(UserCreationForm):
    """
    Form สำหรับการลงทะเบียนผู้ใช้ใหม่ (ขยาย UserCreationForm ของ Django)
    """
    # เพิ่มฟิลด์ที่จำเป็นในการลงทะเบียน (นอกเหนือจาก username, password)
    email = forms.EmailField(required=True, label='อีเมล')
    
    class Meta(UserCreationForm.Meta):
        # ใช้ CustomUser Model ของเรา
        model = CustomUser
        # ฟิลด์ที่ต้องการให้ผู้ใช้กรอก
        fields = UserCreationForm.Meta.fields + (
            'email', 
            'first_name', 
            'last_name', 
            'phone_number'
        )

# ----------------------------------------------------------------------
# 2. Profile Update Form
# ----------------------------------------------------------------------

class UserUpdateForm(UserChangeForm):
    """
    Form สำหรับแก้ไขข้อมูลโปรไฟล์ (ใช้ใน ProfileView)
    """
    # ลบฟิลด์ password ออก เพื่อไม่ให้ผู้ใช้เปลี่ยนรหัสผ่านผ่านฟอร์มนี้
    password = None

    class Meta:
        model = CustomUser
        fields = (
            'first_name', 
            'last_name', 
            'email', 
            'phone_number', 
            'shipping_address', 
            'date_of_birth'
        )
        
        # ปรับการแสดงผลฟิลด์ให้เป็นภาษาไทยและกำหนด Widget
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ตั้งค่าฟิลด์ให้สวยงามด้วย Tailwind-like classes
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'
            })