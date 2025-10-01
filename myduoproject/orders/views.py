from django.shortcuts import render, redirect, get_object_or_404
from products.models import ProductVariant 
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.views.generic import View, TemplateView
from .forms import CheckoutForm
# นำเข้าโมเดลที่จำเป็น
from .models import Cart, CartItem, Order, OrderItem 
from promotions.models import Promotion 
from .cart import CartManager # <--- ใช้ CartManager ตัวเดียวเท่านั้น
import uuid
from decimal import Decimal, InvalidOperation
from promotions.models import Promotion , DiscountType
import json
from django.views.decorators.csrf import csrf_exempt
# ----------------------------------------------------------------------
# *** FIX: ลบฟังก์ชัน _get_or_create_cart(request) ที่ล้าสมัยออก ***
# ตอนนี้ CartManager จะทำหน้าที่นี้ทั้งหมด
# ----------------------------------------------------------------------

@require_POST
def add_to_cart(request):
    """เพิ่มสินค้าลงในตะกร้า (ใช้ CartManager)"""
    # 1. สร้าง CartManager Instance: CartManager จะจัดการการสร้าง/ดึง Cart object
    cart_manager = CartManager(request) 

    variant_id = request.POST.get("variant_id") or request.POST.get("product_id")
    quantity = request.POST.get("quantity", 1)

    if not variant_id:
        return JsonResponse({"error": "Missing variant_id or product_id"}, status=400)

    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError("quantity must be >= 1")
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid quantity"}, status=400)

    # ดึง variant จากฐานข้อมูล
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if variant.stock < quantity:
        return JsonResponse({"error": "สินค้าไม่พอในสต็อก"}, status=400)

    # 2. เพิ่มลงตะกร้า: เรียกใช้เมธอด .add()
    cart_manager.add(variant=variant, quantity=quantity)

    # 3. ดึงยอดรวมเพื่อส่งกลับ
    total_quantity = cart_manager.get_total_quantity()

    return JsonResponse({
        "message": f"เพิ่ม {variant.product.name} ({variant.size}) x {quantity} ลงในตะกร้าแล้ว",
        "cart_total_items": total_quantity, 
    })


class CartSummaryView(TemplateView):
    """
    แสดงหน้ารวมตะกร้าสินค้า (FIX: ใช้ CartManager เพื่อดึง Cart ที่ถูกต้อง)
    """
    # *** เปลี่ยน template_name เป็น cart_summary.html ตามที่คุณกำหนดไว้ด้านล่าง ***
    template_name = 'orders/cart_summary.html' 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. ใช้ CartManager เพื่อดึง Cart ที่ถูกต้อง
        cart_manager = CartManager(self.request) 
        cart = cart_manager.cart
        
        context['cart'] = cart
        # ดึงรายการสินค้า: เนื่องจาก CartManager ดึง Cart ที่ถูกต้องแล้ว รายการนี้จึงถูกต้อง
        context['cart_items'] = cart.items.select_related('variant__product').all() 
        context['total_quantity'] = cart_manager.get_total_quantity()
        return context


@require_POST
def update_cart_item(request):
    """
    อัปเดตจำนวนสินค้าในตะกร้า (ใช้ AJAX)
    FIX: ใช้ CartManager เพื่อความถูกต้องของ Cart ID
    """
    # 1. ดึง CartManager ที่ถูกต้อง
    cart_manager = CartManager(request)
    current_cart = cart_manager.cart
    
    try:
        variant_id = request.POST.get('variant_id') # FIX: ควรใช้ variant_id แทน item_id 
        new_quantity = int(request.POST.get('quantity', 0))
        
        # 2. ค้นหารายการสินค้าและตรวจสอบว่ามีอยู่จริง
        cart_item = get_object_or_404(CartItem, cart=current_cart, variant_id=variant_id)
        
        # 3. ใช้เมธอด .update_quantity() ใน CartManager (ถ้ามี)
        # เนื่องจากเรายังไม่ได้สร้างเมธอด update_quantity ใน cart.py
        # เราจะใช้วิธี update โดยตรงใน view ก่อน
        
        if new_quantity <= 0:
            # ถ้าจำนวนเป็น 0 หรือน้อยกว่า ให้ลบรายการนั้นออก
            item_name = cart_item.variant.product.name
            cart_item.delete()
            messages.info(request, f"ลบ {item_name} ออกจากตะกร้าแล้ว")
        else:
            cart_item.quantity = new_quantity
            # TODO: ควรมีการตรวจสอบสต็อกที่นี่
            cart_item.save()
            messages.success(request, "อัปเดตจำนวนสินค้าเรียบร้อยแล้ว")
        
        # 4. คำนวณยอดรวมใหม่ (ควรรีเฟรช Cart object เพื่อให้ grand_total/subtotal ถูกต้อง)
        current_cart.refresh_from_db()

        # คืนค่าเพื่ออัปเดต UI
        return JsonResponse({
            'success': True, 
            'total_items': cart_manager.get_total_quantity(),
            'new_item_total': f"{cart_item.subtotal:.2f}" if new_quantity > 0 else "0.00", 
            'cart_total_subtotal': f"{current_cart.total_subtotal:.2f}",
            'cart_grand_total': f"{current_cart.grand_total:.2f}",
        })

    except CartItem.DoesNotExist:
         return JsonResponse({'success': False, 'error': 'รายการสินค้าไม่ถูกต้องหรือไม่อยู่ในตะกร้าของคุณ'}, status=404)
    except Exception as e:
        print(f"Error in update_cart_item: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def remove_from_cart(request):
    """
    ลบรายการสินค้าออกจากตะกร้า
    """
    cart_manager = CartManager(request)
    current_cart = cart_manager.cart
    
    cart_item_id = request.POST.get('cart_item_id') 
    
    if cart_item_id:
        try:
            # 1. ค้นหารายการ CartItem และตรวจสอบความเป็นเจ้าของ
            item_to_delete = get_object_or_404(
                CartItem, 
                id=cart_item_id, 
                cart=current_cart
            )
            
            item_name = item_to_delete.variant.product.name

            # 2. ดำเนินการลบ
            item_to_delete.delete()
            
            messages.success(request, f'✅ ลบ {item_name} ออกจากตะกร้าเรียบร้อยแล้ว')
            
        except CartItem.DoesNotExist:
            messages.error(request, 'รายการสินค้าไม่ถูกต้องหรือไม่อยู่ในตะกร้าของคุณ')
        except Exception as e:
            # log the actual error for debugging
            print(f"Error during cart item deletion: {e}") 
            messages.error(request, '❌ เกิดข้อผิดพลาดในการลบสินค้า')
            
    else:
        messages.error(request, 'ไม่พบ ID รายการสินค้าที่ต้องการลบ')

    # 4. Redirect กลับไปยังหน้าตะกร้าสินค้า (orders:cart_summary)
    # ซึ่งตอนนี้ตรงกับชื่อพาธที่เรากำหนดใน orders/urls.py แล้ว
    return redirect('orders:cart') 


@require_POST
def apply_promotion(request):
    """ใช้โค้ดโปรโมชั่นกับตะกร้าสินค้า"""
    code = request.POST.get('code', '').strip().upper()
    
    # 1. ใช้ CartManager เพื่อดึง Cart ที่ถูกต้อง
    cart_manager = CartManager(request)
    cart = cart_manager.cart
    
    cart_total = cart.total_subtotal

    if not code:
        messages.error(request, "กรุณากรอกโค้ดโปรโมชั่น")
        return redirect('orders:cart_summary')

    # ... (ส่วนคำนวณโปรโมชั่นเดิมยังคงถูกต้อง) ...
    try:
        promotion = Promotion.objects.get(code=code)
    except Promotion.DoesNotExist:
        messages.error(request, "โค้ดโปรโมชั่นไม่ถูกต้อง")
        return redirect('orders:cart_summary')

    # ตรวจสอบความถูกต้องอื่นๆ 
    if not promotion.is_valid:
          messages.error(request, "โค้ดโปรโมชั่นนี้หมดอายุหรือถูกใช้ครบจำนวนแล้ว")
          return redirect('orders:cart_summary')

    if cart_total < promotion.min_order_amount:
        messages.error(f"ยอดสั่งซื้อขั้นต่ำสำหรับการใช้โค้ดนี้คือ {promotion.min_order_amount:.2f} บาท")
        return redirect('orders:cart_summary')

    # คำนวณส่วนลด
    discount_value = promotion.discount_value
    discount_amount = Decimal(0.00)
    
    if promotion.discount_type == Promotion.DiscountType.PERCENTAGE: 
        discount_amount = min(Decimal(100), discount_value) / Decimal(100) * cart_total
    elif promotion.discount_type == Promotion.DiscountType.FIXED_AMOUNT: 
        discount_amount = min(cart_total, discount_value)
    else:
        messages.error(request, "ประเภทโปรโมชั่นไม่ถูกต้อง กรุณาติดต่อผู้ดูแลระบบ")
        return redirect('orders:cart_summary')

    # บันทึกส่วนลดลงใน Cart
    cart.promotion_code = code
    cart.discount_amount = discount_amount.quantize(Decimal('0.00'))
    cart.save(update_fields=['promotion_code', 'discount_amount']) 
    
    messages.success(request, f"ใช้โค้ด {code} เรียบร้อยแล้ว! ได้รับส่วนลด {cart.discount_amount:.2f} บาท")
    return redirect('orders:cart_summary')
\
class CheckoutView(View):
    """จัดการขั้นตอนการชำระเงินและการสร้างคำสั่งซื้อ"""
    template_name = 'orders/checkout.html'

    def _get_initial_data(self, request):
        """ดึงข้อมูลเริ่มต้นจาก User Profile สำหรับกรอกในฟอร์ม"""
        initial_data = {}
        if request.user.is_authenticated:
            try:
                # สมมติว่ามี UserProfile หรือโมเดลที่เก็บข้อมูลที่อยู่/ติดต่อ
                # **กรุณาปรับโค้ดส่วนนี้ให้เข้ากับโครงสร้าง Model ของคุณ**
                profile = request.user.userprofile 
                
                initial_data = {
                    'full_name': profile.default_full_name, # หรือ profile.user.get_full_name()
                    'email': profile.user.email,
                    'phone_number': profile.default_phone_number,
                    'shipping_address': profile.default_shipping_address,
                }
            except AttributeError:
                pass
        return initial_data

    def get(self, request, *args, **kwargs):
        # 1. ใช้ CartManager เพื่อดึง Cart ที่ถูกต้อง
        cart_manager = CartManager(request)
        cart = cart_manager.cart
        
        if cart.is_empty():
            messages.warning(request, "ตะกร้าสินค้าว่างเปล่า ไม่สามารถดำเนินการชำระเงินได้")
            return redirect('orders:cart_summary')

        # ดึงข้อมูลเริ่มต้นสำหรับฟอร์ม
        initial_data = self._get_initial_data(request)
        form = CheckoutForm(initial=initial_data) 
        
        # 2. คำนวณยอดรวมและส่วนลดจาก CartManager
        subtotal = cart_manager.get_subtotal()
        grand_total = cart_manager.get_grand_total()
        
        context = {
            'form': form,
            'cart': cart,
            'cart_items': cart.items.select_related('variant__product').all(),
            'subtotal': subtotal,                 # <--- ส่ง Subtotal เข้า Context
            'grand_total': grand_total,           # <--- ส่ง Grand Total เข้า Context
            'discount_amount': cart.discount_amount, # ส่งส่วนลดปัจจุบันเข้า Context
        }
        return render(request, self.template_name, context)

    def _create_order_items(self, new_order, cart_items):
        """สร้าง OrderItem จาก CartItem ที่มีอยู่ (ใช้ bulk_create เพื่อเพิ่มประสิทธิภาพ)"""
        order_items = []
        for cart_item in cart_items:
            order_items.append(
                OrderItem(
                    order=new_order,
                    product=cart_item.variant.product, 
                    product_name=cart_item.variant.product.name,
                    quantity=cart_item.quantity,
                    # บันทึกราคา ณ ขณะนั้น
                    unit_price=cart_item.price_at_addition.quantize(Decimal('0.00')), 
                    variant_size=cart_item.variant.size, 
                )
            )
        OrderItem.objects.bulk_create(order_items)

    def _update_promotion_usage(self, cart):
        """อัปเดตจำนวนครั้งที่ใช้โปรโมชั่น"""
        if cart.promotion_code:
            try:
                # ใช้ select_for_update เพื่อล็อกแถวในฐานข้อมูลชั่วคราวระหว่าง Transaction
                promotion = Promotion.objects.select_for_update().get(code=cart.promotion_code)
                promotion.times_used += 1
                promotion.save(update_fields=['times_used'])
            except Promotion.DoesNotExist:
                messages.warning(self.request, f"ไม่พบรหัสโปรโมชั่น '{cart.promotion_code}' แต่คำสั่งซื้อถูกสร้างแล้ว")
                pass

    @transaction.atomic
    def post(self, request):
        # 1. ใช้ CartManager เพื่อดึง Cart ที่ถูกต้อง
        cart_manager = CartManager(request)
        cart = cart_manager.cart
        
        if not cart.items.exists():
            messages.warning(request, "ตะกร้าสินค้าว่างเปล่า ไม่สามารถดำเนินการต่อได้")
            return redirect('orders:cart_summary')
            
        form = CheckoutForm(request.POST)

        # คำนวณยอดรวมและส่วนลดล่าสุดอีกครั้ง
        subtotal = cart_manager.get_subtotal()
        grand_total = cart_manager.get_grand_total()
        
        if form.is_valid():
            data = form.cleaned_data
            
            # 1. สร้าง Order
            new_order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                
                full_name=data['full_name'],
                email=data['email'],
                phone_number=data['phone_number'],
                shipping_address=data['shipping_address'],
                payment_method=data['payment_method'],
                
                # สรุปทางการเงิน (ใช้ค่าที่คำนวณล่าสุดจาก CartManager)
                total_amount=subtotal.quantize(Decimal('0.00')),
                discount_amount=cart.discount_amount.quantize(Decimal('0.00')),
                grand_total=grand_total.quantize(Decimal('0.00')),
            )
            
            # 2. สร้าง Order Items
            self._create_order_items(new_order, cart.items.all())
            
            # 3. อัปเดต Promotion usage
            self._update_promotion_usage(cart)
                
            # 4. ล้างตะกร้าสินค้า
            cart.items.all().delete() 
            cart.promotion_code = ""
            cart.discount_amount = Decimal('0.00')
            cart.save(update_fields=['promotion_code', 'discount_amount'])
            
            messages.success(request, f"สร้างคำสั่งซื้อ #{new_order.order_number} สำเร็จแล้ว!")
            return redirect('orders:order_detail', order_number=new_order.order_number)

        # หากฟอร์มไม่ถูกต้อง
        context = {
            'cart': cart,
            'form': form,
            'cart_items': cart.items.select_related('variant__product').all(),
            'subtotal': subtotal,                 # <--- ส่ง Subtotal กลับไป
            'grand_total': grand_total,           # <--- ส่ง Grand Total กลับไป
            'discount_amount': cart.discount_amount, 
        }
        messages.error(request, "ข้อมูลการจัดส่งไม่สมบูรณ์ กรุณาตรวจสอบอีกครั้ง")
        return render(request, self.template_name, context)

class OrderDetailView(View):
    """แสดงรายละเอียดคำสั่งซื้อ"""
    template_name = 'orders/order_detail.html'
    
    def get(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number)
        
        is_owner = order.user is not None and order.user == request.user
        is_staff = request.user.is_staff
        
        if not (is_owner or is_staff):
            messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงคำสั่งซื้อนี้")
            return redirect('products:product_list') 
        
        context = {'order': order}
        return render(request, self.template_name, context)
@csrf_exempt # อนุญาตให้ POST request ภายนอกเข้าถึงได้ (ควรใช้ CSRF Token ใน JS เพื่อความปลอดภัย)
@require_POST
def validate_coupon(request):
    """
    ตรวจสอบโค้ดส่วนลดจากฐานข้อมูล และคำนวณมูลค่าส่วนลด
    """
    try:
        # 1. รับและแปลงข้อมูลจาก JSON
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code', '').upper()
        # แปลง subtotal เป็น Decimal เพื่อหลีกเลี่ยงข้อผิดพลาดทางการเงิน
        subtotal = Decimal(data.get('subtotal', 0))
        
    except (json.JSONDecodeError, InvalidOperation, TypeError):
        return JsonResponse({'valid': False, 'message': 'รูปแบบข้อมูลไม่ถูกต้อง'}, status=400)
    
    # ถ้าไม่มีโค้ด ก็ให้จบการทำงาน
    if not coupon_code:
        return JsonResponse({'valid': False, 'message': 'กรุณาใส่โค้ดส่วนลด'})
    
    try:
        # 2. ค้นหาโค้ดในฐานข้อมูล
        # เราใช้ Promotion Model ของคุณ
        promotion = Promotion.objects.get(code=coupon_code)
        
        # 3. ตรวจสอบเงื่อนไขตาม Model Properties และฟิลด์
        
        # 3.1 ตรวจสอบสถานะและวันที่ (ใช้ @property is_valid ที่คุณสร้าง)
        if not promotion.is_valid:
            # ใช้ property is_valid ที่อยู่ใน Model.py ของคุณ
            return JsonResponse({
                'valid': False, 
                'message': 'โค้ดนี้ถูกปิดใช้งาน หรือหมดอายุ/ใช้ครบจำนวนแล้ว'
            })
            
        # 3.2 ตรวจสอบยอดสั่งซื้อขั้นต่ำ
        if subtotal < promotion.min_order_amount:
             return JsonResponse({
                'valid': False, 
                'message': f'ยอดสั่งซื้อขั้นต่ำสำหรับโค้ดนี้คือ {promotion.min_order_amount.quantize(Decimal("0.01"))} บาท'
             })
        
        # 4. คำนวณมูลค่าส่วนลด
        
        if promotion.discount_type == DiscountType.PERCENTAGE:
            # คำนวณส่วนลดแบบเปอร์เซ็นต์
            discount_amount = subtotal * (promotion.discount_value / Decimal(100))
        elif promotion.discount_type == DiscountType.FIXED_AMOUNT:
            # คำนวณส่วนลดแบบจำนวนเงินคงที่
            discount_amount = promotion.discount_value
        else:
            discount_amount = Decimal(0)

        # 5. ตรวจสอบให้แน่ใจว่าส่วนลดไม่เกินยอดรวมสินค้า
        final_discount = min(discount_amount, subtotal)
        final_discount = final_discount.quantize(Decimal("0.01"))
        
        # 6. ส่งผลลัพธ์กลับในรูปแบบ JSON
        return JsonResponse({
            'valid': True,
            'discount_amount': final_discount,
            'message': 'ใช้โค้ดส่วนลดสำเร็จ'
        })
        
    except Promotion.DoesNotExist:
        # ไม่พบโค้ดในฐานข้อมูล
        return JsonResponse({'valid': False, 'message': 'ไม่พบโค้ดส่วนลดนี้'})
    
    except Exception as e:
        # การจัดการข้อผิดพลาดทั่วไป
        print(f"Error processing coupon: {e}")
        return JsonResponse({'valid': False, 'message': 'เกิดข้อผิดพลาดภายในระบบ'}, status=500)