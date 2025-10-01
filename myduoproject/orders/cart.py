from django.db import transaction
from django.db.models import Sum, F, DecimalField # เพิ่ม F และ DecimalField
from django.http import HttpRequest
from decimal import Decimal
from django.apps import apps 

# นำเข้าโมเดล Cart และ CartItem จากไฟล์ orders.models ปัจจุบัน
from .models import Cart, CartItem 

# -------------------------------------------------------------------
# FIX: การ Import ProductVariant อย่างถูกต้อง
# -------------------------------------------------------------------
try:
    ProductVariant = apps.get_model('products', 'ProductVariant')
except LookupError:
    print("FATAL ERROR: Could not find ProductVariant model in the 'products' application.")
    raise

# -------------------------------------------------------------------

class CartManager:
    """
    Class ที่จัดการการดำเนินการทั้งหมดของตะกร้าสินค้า (เพิ่ม ลบ อัปเดต)
    CartManager จะถูกสร้างขึ้นในแต่ละ request เพื่อจัดการ Cart object ที่เกี่ยวข้อง
    """
    
    def __init__(self, request: HttpRequest):
        """
        ตรวจสอบและดึง Cart object สำหรับผู้ใช้/session
        """
        self.request = request
        self.user = self.request.user if self.request.user.is_authenticated else None
        
        # 1. ตรวจสอบ session key และสร้างถ้าไม่มี (สำหรับ Guest)
        if not self.request.session.session_key:
            self.request.session.create()
        self.session_key = self.request.session.session_key

        # 2. หาหรือสร้าง Cart 
        self.cart = self._get_or_create_cart()

    def _get_or_create_cart(self) -> Cart:
        """Logic สำหรับดึง, สร้าง, หรือรวม Cart"""
        if self.user:
            # 2a. จัดการ Cart สำหรับผู้ใช้ที่ล็อกอิน
            user_cart = Cart.objects.filter(user=self.user).first()
            session_cart = Cart.objects.filter(session_key=self.session_key, user__isnull=True).first()
            
            if not user_cart and session_cart:
                # ถ้า User ไม่มี Cart แต่มี Cart ของ Guest ใน Session ปัจจุบัน -> ผูก Cart
                session_cart.user = self.user
                session_cart.session_key = None
                session_cart.save()
                return session_cart
            elif user_cart and session_cart and user_cart.id != session_cart.id: # ตรวจสอบ ID เพื่อป้องกันการผสานตัวเอง
                # ถ้า User มี Cart แล้ว และมี Guest Cart ที่ยังไม่ถูกผสาน
                self._merge_session_cart(user_cart, session_cart)
                return user_cart
            elif not user_cart:
                # ถ้าไม่มี Cart ทั้งแบบ User และ Session -> สร้างใหม่
                return Cart.objects.create(user=self.user)
            
            # 2b. ถ้ามี Cart ของ User อยู่แล้ว
            if user_cart and user_cart.session_key:
                # ล้าง session_key หากมีการล็อกอิน
                user_cart.session_key = None
                user_cart.save(update_fields=['session_key'])

            return user_cart

        else:
            # 2c. จัดการ Cart สำหรับผู้มาเยือน (Guest)
            cart, created = Cart.objects.get_or_create(session_key=self.session_key, user__isnull=True)
            return cart

    @transaction.atomic
    def _merge_session_cart(self, user_cart: Cart, guest_cart: Cart):
        """รวมรายการสินค้าจาก Cart ของ Guest เข้าสู่ Cart ของ User"""
        
        # ย้ายรายการสินค้าทั้งหมดจาก Guest Cart ไป User Cart
        for guest_item in guest_cart.items.all():
            # เรียกใช้เมธอด add เพื่อให้มีการตรวจสอบและรวม item ที่ซ้ำกัน
            # NOTE: ต้องตั้งค่า self.cart ให้เป็น user_cart ชั่วคราวเพื่อให้ self.add ทำงานกับ user_cart
            original_cart = self.cart
            self.cart = user_cart
            self.add(
                variant=guest_item.variant, 
                quantity=guest_item.quantity, 
                price_override=guest_item.price_at_addition 
            )
            self.cart = original_cart # คืนค่า self.cart เดิม
        
        # ลบ Guest Cart เดิม
        guest_cart.delete()

    @transaction.atomic
    def add(self, variant, quantity: int = 1, price_override: Decimal = None):
        """
        เมธอดหลักในการเพิ่ม ProductVariant ลงใน Cart หรืออัปเดตจำนวน
        """
        # 1. ตรวจสอบราคาที่จะใช้
        try:
            unit_price = price_override if price_override is not None else variant.current_price
        except AttributeError:
             raise AttributeError("ProductVariant must have a 'current_price' attribute.")
        
        try:
            # 2. ลองค้นหารายการสินค้าในตะกร้าที่มีอยู่แล้ว (ส่วน Get/Update)
            cart_item = CartItem.objects.get(
                cart=self.cart,
                variant_id=variant.id, 
            )
            
            # 3. ถ้ารายการสินค้ามีอยู่: อัปเดตจำนวนและราคา
            cart_item.quantity += quantity
            cart_item.price_at_addition = unit_price # อัปเดตราคาล่าสุด
            cart_item.save(update_fields=['quantity', 'price_at_addition', 'updated_at'])

        except CartItem.DoesNotExist:
            # 4. ถ้ารายการสินค้าไม่มีอยู่: สร้างรายการใหม่ (ส่วน Create)
            cart_item = CartItem.objects.create(
                cart=self.cart,
                variant=variant, 
                quantity=quantity,
                price_at_addition=unit_price
            )

        # TODO: self.cart.apply_promotions() 
        return cart_item

    def get_total_quantity(self) -> int:
        """นับจำนวนรวมของชิ้นสินค้าทั้งหมดในตะกร้า"""
        result = self.cart.items.aggregate(total_quantity=Sum('quantity'))
        return result['total_quantity'] or 0

    # ***************************************************************
    # FIX: เพิ่มเมธอดสำหรับคำนวณยอดรวม (Subtotal) และยอดสุทธิ (Grand Total)
    # ***************************************************************
    def get_subtotal(self) -> Decimal:
        """คำนวณยอดรวมสินค้าทั้งหมดในตะกร้า (ก่อนส่วนลด)"""
        # คำนวณยอดรวมของ (quantity * price_at_addition)
        subtotal = self.cart.items.aggregate(
            subtotal=Sum(F('quantity') * F('price_at_addition'), output_field=DecimalField())
        )['subtotal']
        
        return subtotal.quantize(Decimal('0.00')) if subtotal else Decimal('0.00')

    def get_grand_total(self) -> Decimal:
        """คำนวณยอดรวมสุทธิ (หลังส่วนลด)"""
        subtotal = self.get_subtotal()
        discount = self.cart.discount_amount if self.cart.discount_amount else Decimal('0.00')
        
        grand_total = subtotal - discount
        # ป้องกันไม่ให้ราคารวมติดลบ
        return max(Decimal('0.00'), grand_total).quantize(Decimal('0.00'))
