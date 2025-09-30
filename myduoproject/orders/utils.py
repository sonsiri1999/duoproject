from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
# สมมติว่าคุณมี ProductVariant ที่จำเป็นต้องใช้ในการอ้างอิง
# from products.models import ProductVariant 
# หากไม่ใช้ ProductVariant ที่นี่ ก็ไม่จำเป็นต้อง import ครับ

# ----------------------------------------------------------------------
# ฟังก์ชันสำหรับจัดการ Session Cart
# ----------------------------------------------------------------------
def get_cart_session(request):
    """
    ดึงข้อมูลตะกร้าสินค้าจาก session
    ตะกร้าจะเก็บในรูปแบบ: {variant_id: {'quantity': N, 'price': 'X.XX'}}
    """
    # ตรวจสอบว่ามีตะกร้าใน session หรือไม่
    if 'cart' not in request.session:
        # หากไม่มีตะกร้า ให้สร้างตะกร้าว่าง
        request.session['cart'] = {}
        # **สำคัญ:** ต้องบังคับให้ Django บันทึก session เมื่อมีการสร้าง/เปลี่ยนแปลงโครงสร้าง
        request.session.modified = True 
        
    return request.session.get('cart', {})


# ----------------------------------------------------------------------
# ฟังก์ชันสำหรับคำนวณยอดรวม
# ----------------------------------------------------------------------
def calculate_cart_totals(cart, promotions=None):
    """
    คำนวณยอดรวม (Subtotal) ของสินค้าในตะกร้า
    """
    subtotal = Decimal('0.00')
    
    for item_id, item_data in cart.items():
        # ตรวจสอบว่าข้อมูลครบถ้วนหรือไม่
        if 'quantity' in item_data and 'price' in item_data:
            try:
                quantity = item_data['quantity']
                # แปลงราคาที่เก็บเป็น String ใน Session กลับไปเป็น Decimal
                price = Decimal(item_data['price'])
                subtotal += price * quantity
            except (KeyError, TypeError, ValueError):
                # จัดการข้อผิดพลาดถ้าข้อมูลใน session เสียหาย
                continue
        
    # ในอนาคตสามารถเพิ่ม logic คำนวณส่วนลดจาก promotions ที่นี่ได้
    discount = Decimal('0.00')
    
    # ค่าจัดส่ง: ดึงจาก settings หรือกำหนดค่าคงที่
    shipping_cost = getattr(settings, 'DEFAULT_SHIPPING_COST', Decimal('50.00'))
    
    total_amount = subtotal - discount + shipping_cost
    
    return {
        'subtotal': subtotal.quantize(Decimal('0.00')),
        'discount': discount.quantize(Decimal('0.00')),
        'shipping_cost': shipping_cost.quantize(Decimal('0.00')),
        'total_amount': total_amount.quantize(Decimal('0.00')),
        'total_items': sum(item['quantity'] for item in cart.values() if 'quantity' in item),
    }

# ----------------------------------------------------------------------
# ฟังก์ชันเสริมสำหรับการจัดการสินค้าในตะกร้า (ตัวอย่าง)
# ----------------------------------------------------------------------

def add_item_to_cart(request, variant_id, quantity, price):
    """เพิ่มสินค้าลงในตะกร้าและบันทึก session"""
    cart = get_cart_session(request)
    variant_id_str = str(variant_id)

    if variant_id_str in cart:
        cart[variant_id_str]['quantity'] += quantity
    else:
        cart[variant_id_str] = {
            'quantity': quantity,
            'price': str(price) # เก็บราคาเป็น String
        }
    
    request.session.modified = True
    return cart

def remove_item_from_cart(request, variant_id, quantity_to_remove=None):
    """ลบสินค้าบางส่วนหรือทั้งหมดออกจากตะกร้า"""
    cart = get_cart_session(request)
    variant_id_str = str(variant_id)
    
    if variant_id_str in cart:
        if quantity_to_remove is None or quantity_to_remove >= cart[variant_id_str]['quantity']:
            # ลบทั้งรายการ
            del cart[variant_id_str]
        else:
            # ลบบางส่วน
            cart[variant_id_str]['quantity'] -= quantity_to_remove
            
        request.session.modified = True
        return True
    return False