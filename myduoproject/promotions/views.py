from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from promotions.models import Promotion # นำเข้า Promotion model
from orders.models import get_active_cart, calculate_discount_amount # นำเข้าฟังก์ชันจาก orders.models

# ----------------------------------------------------------------------
# Logic ของ Promotion
# ----------------------------------------------------------------------

@require_POST
def apply_promotion(request):
    """
    Handles AJAX request to validate, apply a coupon code, and update the cart totals.
    """
    # 1. รับโค้ดจาก AJAX request
    try:
        data = request.POST 
        code = data.get('code', '').strip().upper()
    except Exception:
        # ใช้ 500 status code เพื่อแสดงว่าเกิดข้อผิดพลาดภายใน
        return JsonResponse({'success': False, 'message': 'รูปแบบข้อมูลไม่ถูกต้อง', 'status': 500})

    if not code:
        return JsonResponse({'success': False, 'message': 'กรุณาใส่โค้ดส่วนลด'})

    # 2. ค้นหา Cart ของผู้ใช้
    cart = get_active_cart(request)
    if not cart:
        return JsonResponse({'success': False, 'message': 'ไม่พบตะกร้าสินค้า กรุณาลองเพิ่มสินค้าก่อน'})

    try:
        # 3. ค้นหา Promotion ในฐานข้อมูล
        promotion = Promotion.objects.get(code=code)
    except Promotion.DoesNotExist:
        # 3a. ไม่พบโค้ด
        return JsonResponse({'success': False, 'message': f'ไม่พบโค้ดส่วนลด "{code}"'})

    # 4. ตรวจสอบความถูกต้องของโค้ด (วันที่, สถานะ, จำนวนครั้งที่ใช้)
    if not promotion.is_valid:
        # ตรวจสอบว่าโค้ดหมดอายุ, ถูกปิด, หรือใช้ครบจำนวนแล้วหรือไม่
        return JsonResponse({'success': False, 'message': 'โค้ดส่วนลดนี้หมดอายุ, ถูกระงับ, หรือถูกใช้ครบจำนวนแล้ว'})

    # 5. ตรวจสอบยอดสั่งซื้อขั้นต่ำ
    # ใช้ Decimal ในการเปรียบเทียบ
    subtotal = cart.total_subtotal
    if subtotal < promotion.min_order_amount:
        return JsonResponse({
            'success': False, 
            'message': f'ยอดสั่งซื้อขั้นต่ำต้องถึง {promotion.min_order_amount:.2f} บาท (ยอดปัจจุบัน: {subtotal:.2f})'
        })
    
    # 6. ตรวจสอบว่ามีรายการสินค้าในตะกร้าหรือไม่
    if cart.is_empty():
         return JsonResponse({'success': False, 'message': 'ไม่สามารถใช้โค้ดได้ ตะกร้าสินค้าว่างเปล่า'})

    # 7. คำนวณส่วนลดและบันทึกใน Cart
    discount_amount = calculate_discount_amount(subtotal, promotion)
    
    # อัปเดต Cart
    # ใช้ transaction เพื่อป้องกันข้อผิดพลาด
    try:
        with transaction.atomic():
            cart.promotion_code = code
            cart.discount_amount = discount_amount
            cart.save()
            
            # Note: เราจะเพิ่ม times_used ใน Promotion Model ก็ต่อเมื่อมีการยืนยันคำสั่งซื้อจริงๆ
            # แต่เพื่อการทดสอบเบื้องต้น ให้ถือว่าโค้ดถูก "ใช้" ในเซสชันนี้แล้ว

    except Exception as e:
        print(f"Error applying promotion: {e}")
        return JsonResponse({'success': False, 'message': 'เกิดข้อผิดพลาดในการบันทึกส่วนลด'})

    # 8. ส่งค่ากลับพร้อมส่วนลดใหม่
    return JsonResponse({
        'success': True, 
        'message': f'ใช้โค้ดส่วนลด "{code}" สำเร็จ! คุณประหยัดได้ {discount_amount:.2f} บาท',
        'discount_amount': f'{discount_amount:.2f}',
        'grand_total': f'{cart.grand_total:.2f}',
        'promotion_code': code,
    })


@require_POST
def remove_promotion(request):
    """
    Handles AJAX request to remove an applied coupon code from the user's cart.
    """
    cart = get_active_cart(request)
    
    if cart and cart.promotion_code:
        # รีเซ็ตส่วนลด
        cart.promotion_code = None
        cart.discount_amount = Decimal('0.00')
        cart.save()

    # ส่งค่ากลับ (แม้ Cart จะไม่มีอยู่ หรือไม่มีโค้ดอยู่แล้ว ก็ต้องส่งค่ากลับที่รีเซ็ตแล้ว)
    return JsonResponse({
        'success': True,
        'message': 'ยกเลิกโค้ดส่วนลดแล้ว',
        'discount_amount': '0.00',
        'grand_total': f'{cart.grand_total:.2f}' if cart else '0.00',
        'promotion_code': None
    })
