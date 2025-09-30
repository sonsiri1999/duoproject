from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View 
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from decimal import Decimal # ต้อง import Decimal เพื่อให้แน่ใจว่าใช้ในการคำนวณ

from .models import Product, ProductVariant
from .forms import ProductCreateForm 
from orders.utils import get_cart_session # ดึงฟังก์ชันจัดการ Session Cart

# Test function for staff access
def is_staff(user):
    """ตรวจสอบว่าผู้ใช้เป็น Staff หรือไม่"""
    return user.is_staff

# ----------------------------------------------------------------------
# Public Views (Class-Based)
# ----------------------------------------------------------------------

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        """กรองสินค้าตามสถานะ: Pre-order หรือ Available"""
        return Product.objects.filter(status__in=['PRE_ORDER', 'AVAILABLE']).order_by('-created_at')

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    
    def get_object(self, queryset=None):
        """ดึงสินค้าตาม slug ที่ส่งมาใน URL"""
        return get_object_or_404(Product, slug=self.kwargs.get('slug'))
    
# ----------------------------------------------------------------------
# AJAX / Cart Interaction (Function-Based)
# ----------------------------------------------------------------------
@require_POST
def add_to_cart(request):
    """จัดการการเพิ่ม ProductVariant ลงใน Session Cart (AJAX endpoint)"""
    try:
        variant_id = request.POST.get('variant_id')
        # ตรวจสอบและแปลง quantity เป็น int ถ้าแปลงไม่ได้ให้ใช้ค่าเริ่มต้น 1
        quantity = int(request.POST.get('quantity', 1)) 
        
        if not variant_id:
             return JsonResponse({'success': False, 'message': 'กรุณาเลือกตัวเลือกสินค้า'}, status=400)

        variant = get_object_or_404(ProductVariant, pk=variant_id)
        
        if quantity <= 0:
            return JsonResponse({'success': False, 'message': 'จำนวนสินค้าต้องมากกว่า 0'}, status=400)
            
        # ดึงหรือสร้าง Session Cart
        cart = get_cart_session(request)
        cart_key = str(variant_id)
        
        # ราคาต้องแปลงเป็น String ก่อนเก็บใน Session (ตามหลักการของ Django Session)
        price_str = str(variant.current_price.quantize(Decimal('0.00')))
        
        # เพิ่ม/อัปเดตสินค้า
        if cart_key in cart:
            cart[cart_key]['quantity'] += quantity
        else:
            cart[cart_key] = {
                'quantity': quantity,
                'price': price_str 
            }
        
        # บันทึก Session: สำคัญมาก
        request.session.modified = True
        
        # คำนวณจำนวนสินค้ารวม
        total_items = sum(item.get('quantity', 0) for item in cart.values())
        
        return JsonResponse({'success': True, 'total_items': total_items})
        
    except ProductVariant.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'ตัวเลือกสินค้าไม่ถูกต้อง'}, status=404)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'จำนวนสินค้าไม่ถูกต้อง'}, status=400)
    except Exception as e:
        # Log error
        print(f"Error adding to cart: {e}")
        return JsonResponse({'success': False, 'message': 'เกิดข้อผิดพลาดในการเพิ่มสินค้า'}, status=500)


# ----------------------------------------------------------------------
# Staff/Admin Views (Class-Based)
# ----------------------------------------------------------------------
@method_decorator(user_passes_test(is_staff), name='dispatch')
class ProductCreateView(View):
    """
    Custom view for staff to add new products and their default variant.
    """
    template_name = 'products/add_product.html'
    
    def get(self, request):
        form = ProductCreateForm()
        return render(request, self.template_name, {'form': form})
        
    def post(self, request):
        form = ProductCreateForm(request.POST, request.FILES) 
        
        if form.is_valid():
            product = form.save()
            messages.success(request, f'สินค้า "{product.name}" ถูกสร้างและบันทึกลงในระบบแล้ว')
            # เปลี่ยนเส้นทางไปหน้ารายละเอียดสินค้าใหม่
            return redirect('products:product_detail', slug=product.slug) 
        
        # แสดงข้อผิดพลาดหากฟอร์มไม่ถูกต้อง
        messages.error(request, 'กรุณาแก้ไขข้อผิดพลาดในแบบฟอร์ม')
        return render(request, self.template_name, {'form': form})
