from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    """
    Custom User Model ที่ขยาย AbstractUser เพื่อเพิ่มข้อมูลเฉพาะสำหรับร้านค้า
    """
    
    # 1. ข้อมูลติดต่อ
    email = models.EmailField(_('อีเมล'), unique=True)
    phone_number = models.CharField(_('เบอร์โทรศัพท์'), max_length=20, blank=True, null=True)
    
    # 2. ข้อมูลที่อยู่จัดส่งเริ่มต้น (ใช้ในการ Checkout)
    shipping_address = models.TextField(_('ที่อยู่จัดส่งเริ่มต้น'), blank=True, null=True)
    
    # 3. ข้อมูลอื่น ๆ
    date_of_birth = models.DateField(_('วันเกิด'), blank=True, null=True)
    
    # กำหนดให้ใช้ email เป็นฟิลด์สำหรับ Login แทน username (optional)
    # USERNAME_FIELD = 'email' 
    # REQUIRED_FIELDS = ['username'] # ถ้าใช้ email เป็น USERNAME_FIELD ต้องเพิ่ม username เข้ามา

    class Meta:
        verbose_name = _('บัญชีผู้ใช้')
        verbose_name_plural = _('บัญชีผู้ใช้')

    def __str__(self):
        return self.email or self.username