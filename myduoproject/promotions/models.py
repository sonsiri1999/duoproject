from django.db import models
from django.utils.translation import gettext_lazy as _

class DiscountType(models.TextChoices):
    PERCENTAGE = 'PERCENT', _('เปอร์เซ็นต์ (%)')
    FIXED_AMOUNT = 'FIXED', _('จำนวนเงินคงที่ (บาท)')

class Promotion(models.Model):
    """
    Model สำหรับโค้ดโปรโมชั่นหรือส่วนลด
    """
    code = models.CharField(_('โค้ดโปรโมชั่น'), max_length=50, unique=True)
    
    # ประเภทและมูลค่าส่วนลด
    discount_type = models.CharField(
        _('ประเภทส่วนลด'),
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.FIXED_AMOUNT
    )
    discount_value = models.DecimalField(_('มูลค่าส่วนลด'), max_digits=10, decimal_places=2)
    
    # เงื่อนไขการใช้งาน
    min_order_amount = models.DecimalField(
        _('ยอดสั่งซื้อขั้นต่ำ'), 
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        help_text=_("ยอดสั่งซื้อขั้นต่ำที่สามารถใช้โค้ดนี้ได้")
    )
    
    # การจำกัด
    is_active = models.BooleanField(_('เปิดใช้งาน'), default=True)
    valid_from = models.DateTimeField(_('ใช้ได้ตั้งแต่'))
    valid_to = models.DateTimeField(_('ใช้ได้ถึง'))
    
    # จำนวนจำกัด
    max_uses = models.PositiveIntegerField(_('จำนวนครั้งที่ใช้ได้สูงสุด'), default=0) # 0 = ไม่จำกัด
    times_used = models.PositiveIntegerField(_('จำนวนครั้งที่ถูกใช้ไป'), default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('โค้ดโปรโมชั่น')
        verbose_name_plural = _('โค้ดโปรโมชั่น')
        ordering = ['-valid_to']

    def __str__(self):
        return self.code

    @property
    def is_valid(self):
        """Checks if the promotion is currently active based on dates and usage."""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
            
        if self.valid_from > now or self.valid_to < now:
            return False
            
        if self.max_uses > 0 and self.times_used >= self.max_uses:
            return False
            
        return True