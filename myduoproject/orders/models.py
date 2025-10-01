from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid
import time
from promotions.models import Promotion, DiscountType # นำเข้า Promotion จาก app promotions
from django.contrib.auth import get_user_model # เพื่อใช้ User model
from django.http import HttpRequest
# *** ไม่ต้อง Import ProductVariant ที่นี่ เพื่อหลีกเลี่ยง Conflict ***

# สมมติว่า Product และ ProductVariant อยู่ใน app 'products'
PRODUCT_APP_NAME = 'products'
USER_MODEL = get_user_model() 

class OrderStatus(models.TextChoices):
    PENDING = 'PENDING', _('รอดำเนินการชำระเงิน')
    PAID = 'PAID', _('ชำระเงินแล้ว')
    SHIPPED = 'SHIPPED', _('กำลังจัดส่ง')
    DELIVERED = 'DELIVERED', _('จัดส่งสำเร็จ')
    CANCELLED = 'CANCELLED', _('ยกเลิก')

class PaymentMethod(models.TextChoices):
    BANK = 'BANK', _('โอนเงินผ่านธนาคาร')
    CREDIT = 'CREDIT', _('บัตรเครดิต/เดบิต')
    COD = 'COD', _('เก็บเงินปลายทาง')
    
# --- CART MODELS ---

class Cart(models.Model):
    user = models.OneToOneField(USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    promotion_code = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Guest Cart ({self.session_key or 'No Session'})"

    @property
    def total_subtotal(self):
        """คำนวณยอดรวมของสินค้าทั้งหมดก่อนหักส่วนลด"""
        return sum(item.subtotal for item in self.items.all()) if self.items.exists() else Decimal('0.00')

    @property
    def grand_total(self):
        """คำนวณยอดรวมสุทธิหลังหักส่วนลดแล้ว"""
        subtotal = self.total_subtotal
        return max(Decimal('0.00'), subtotal - self.discount_amount)
    
    def is_empty(self):
        """ตรวจสอบว่าตะกร้ามีรายการสินค้าหรือไม่"""
        return self.items.count() == 0


class CartItem(models.Model):
    """
    รายการสินค้าแต่ละชิ้นภายในตะกร้า (Cart)
    """
    # *** FIX: ใช้ String Reference ที่ถูกต้องเพียงครั้งเดียวเพื่อชี้ไปยังโมเดลภายนอก ***
    variant = models.ForeignKey(f'{PRODUCT_APP_NAME}.ProductVariant', on_delete=models.CASCADE, verbose_name=_("ตัวเลือกสินค้า"))
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name=_("ตะกร้า"))
    
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("จำนวน"))
    
    # บันทึกราคาตอนเพิ่มลงตะกร้า (เพื่อป้องกันราคาเปลี่ยนแปลง)
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("ราคาต่อหน่วย"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("รายการสินค้าในตะกร้า")
        verbose_name_plural = _("รายการสินค้าในตะกร้า")
        unique_together = ('cart', 'variant') 

    def __str__(self):
        # NOTE: การเข้าถึง variant.product.name อาจทำให้เกิด DoesNotExist หากไม่มี product.name
        # แต่ในทางปฏิบัติควรทำงานได้ถ้าโมเดลมีการตั้งค่าถูกต้อง
        try:
            return f"{self.quantity} x {self.variant.product.name} ({self.variant.size})"
        except AttributeError:
             return f"{self.quantity} x Item ID: {self.variant_id}"

    @property
    def subtotal(self):
        """Calculates the subtotal for this specific item."""
        return self.quantity * self.price_at_addition
        
    @property
    def product_name(self):
        """ดึงชื่อสินค้าหลักจาก variant"""
        try:
            return self.variant.product.name
        except AttributeError:
            return "(ไม่พบชื่อสินค้า)"

    @property
    def variant_name(self):
        """ดึงชื่อตัวเลือก เช่น ขนาด/สี จาก variant"""
        try:
            return self.variant.size
        except AttributeError:
            return ""
# --- END CART MODELS ---


# --- HELPER FUNCTIONS FOR PROMOTION VIEWS ---

# NOTE: ฟังก์ชัน get_active_cart และ calculate_discount_amount 
# ควรอยู่ในไฟล์ utilities.py หรือ services.py มากกว่า models.py แต่ถูกคงไว้ตามต้นฉบับ
def get_active_cart(request: HttpRequest) -> Cart | None:
    """ 
    Retrieves the active cart, prioritizing logged-in user's cart, 
    or falling back to the session key for guests.
    """
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return cart
        except Cart.DoesNotExist:
            cart = Cart.objects.create(user=request.user)
            return cart
    
    session_key = request.session.session_key
    if session_key:
        try:
            cart = Cart.objects.get(session_key=session_key, user__isnull=True)
            return cart
        except Cart.DoesNotExist:
            return None
    return None

def calculate_discount_amount(subtotal: Decimal, promotion: Promotion) -> Decimal:
    """ 
    Calculates the discount amount based on the promotion rules and the cart subtotal.
    """
    discount = Decimal('0.00')
    value = promotion.discount_value
    
    if promotion.discount_type == DiscountType.PERCENTAGE:
        calculated_discount = subtotal * (value / 100)
        discount = calculated_discount
    elif promotion.discount_type == DiscountType.FIXED_AMOUNT:
        discount = value
    
    return min(discount, subtotal)

# --- ORDER MODELS ---

class Order(models.Model):
    """
    คำสั่งซื้อที่ถูกยืนยันแล้ว
    """
    order_number = models.CharField(max_length=20, unique=True, verbose_name=_("หมายเลขคำสั่งซื้อ"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("ผู้สั่งซื้อ"))
    status = models.CharField(max_length=10, choices=OrderStatus.choices, default=OrderStatus.PENDING, verbose_name=_("สถานะคำสั่งซื้อ"))

    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True,         
        blank=True,        
        verbose_name=_("ยอดรวมสินค้า (ก่อนส่วนลด)")
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("มูลค่าส่วนลด"))
    grand_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True,         # อนุญาตให้เป็น NULL ในฐานข้อมูล
        blank=True,        # อนุญาตให้ว่างในฟอร์ม Django
        verbose_name=_("ยอดชำระสุทธิ")
    )
    
    full_name = models.CharField(max_length=255, verbose_name=_("ชื่อ-นามสกุล ผู้รับ"))
    email = models.EmailField(max_length=255, verbose_name=_("อีเมลติดต่อ"))
    phone_number = models.CharField(max_length=20, verbose_name=_("เบอร์โทรศัพท์"))
    shipping_address = models.TextField(verbose_name=_("ที่อยู่จัดส่ง"))
    
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.BANK, verbose_name=_("ช่องทางการชำระเงิน"))
    payment_slip = models.FileField(
        upload_to='payment_slips/%Y/%m/%d/', 
        null=True, 
        blank=True, 
        verbose_name='สลิปหลักฐานการโอนเงิน'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("คำสั่งซื้อ")
        verbose_name_plural = _("คำสั่งซื้อ")
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number
    
    def save(self, *args, **kwargs):
        """Generate a unique order number if it's a new record."""
        if not self.order_number:
            self.order_number = f"{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """
    รายละเอียดสินค้าแต่ละชิ้นในคำสั่งซื้อ (Snapshot ของสินค้า)
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name=_("คำสั่งซื้อ"))
    
    # *** FIX: ใช้ String Reference สำหรับ Product ***
    product = models.ForeignKey(f'{PRODUCT_APP_NAME}.Product', on_delete=models.SET_NULL, null=True, verbose_name=_("สินค้าหลัก")) 
    product_name = models.CharField(max_length=255, verbose_name=_("ชื่อสินค้า"))
    variant_size = models.CharField(max_length=100, verbose_name=_("ตัวเลือก/ขนาด"))
    
    quantity = models.PositiveIntegerField(verbose_name=_("จำนวน"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("ราคาต่อหน่วย"))

    class Meta:
        verbose_name = _("รายการสินค้าในคำสั่งซื้อ")
        verbose_name_plural = _("รายการสินค้าในคำสั่งซื้อ")

    @property
    def subtotal(self):
        return self.quantity * self.unit_price
        
    def __str__(self):
        return f"{self.quantity} x {self.product_name} ({self.variant_size})"
