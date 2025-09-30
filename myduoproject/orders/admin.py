from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem

# ----------------------------------------------------------------------
# Inline for Order Items
# ----------------------------------------------------------------------

class OrderItemInline(admin.TabularInline):
    """
    แสดงรายการสินค้าใน Order ภายใต้หน้า Order Admin
    """
    model = OrderItem
    extra = 0
    # ฟิลด์ที่ใช้ใน OrderItem models คือ unit_price (ราคาต่อหน่วย)
    readonly_fields = ('product', 'product_name', 'variant_size', 'unit_price', 'quantity', 'subtotal',)
    fields = ('product', 'product_name', 'variant_size', 'unit_price', 'quantity', 'subtotal',)
    can_delete = False

    # ปิดการเพิ่ม item ใหม่ตรงๆ จากหน้า Admin (ควรสร้างผ่าน process checkout เท่านั้น)
    def has_add_permission(self, request, obj=None):
        return False
        
    @admin.display(description='รวม')
    def subtotal(self, obj):
        # ใช้ subtotal property ที่เรากำหนดใน models.py
        return f"{obj.subtotal:.2f} บาท"

# ----------------------------------------------------------------------
# Order Admin
# ----------------------------------------------------------------------

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 
        'user', 
        'display_total_amount', 
        'discount_amount', 
        'grand_total', 
        'status', 
        'created_at'
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'full_name', 'email', 'phone_number')
    
    # แก้ไข readonly_fields ให้ตรงกับชื่อฟิลด์จริง
    readonly_fields = (
        'order_number', 
        'user', 
        'total_amount', # แก้จาก 'subtotal'
        'discount_amount', 
        'grand_total', 
        'created_at', # แก้จาก 'order_date'
        'updated_at',
        'full_name', 
        'email', 
        'phone_number', 
        'shipping_address',
        'payment_method'
    )
    
    fieldsets = (
        ('ข้อมูลคำสั่งซื้อหลัก', {
            'fields': ('order_number', 'user', 'status', 'payment_method', 'created_at'),
        }),
        ('สรุปการเงิน', {
            'fields': ('total_amount', 'discount_amount', 'grand_total'),
        }),
        ('ที่อยู่จัดส่งและผู้ติดต่อ', {
            'fields': ('full_name', 'email', 'phone_number', 'shipping_address'),
        }),
    )
    
    # แก้ไข ordering ให้ใช้ created_at
    ordering = ('-created_at',) 
    
    inlines = [OrderItemInline]

    @admin.display(description='ยอดรวมสินค้า')
    def display_total_amount(self, obj):
        return f"{obj.total_amount:.2f} บาท"


# ----------------------------------------------------------------------
# Cart Admin
# ----------------------------------------------------------------------

class CartItemInline(admin.TabularInline):
    model = CartItem
    readonly_fields = ('variant', 'quantity', 'price_at_addition', 'subtotal',)
    fields = ('variant', 'quantity', 'price_at_addition', 'subtotal',)
    extra = 0
    can_delete = False
    
    @admin.display(description='รวม')
    def subtotal(self, obj):
        return f"{obj.subtotal:.2f} บาท"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'total_subtotal', 'discount_amount', 'grand_total', 'updated_at')
    search_fields = ('user__username', 'session_key')
    list_filter = ('updated_at', 'created_at', 'user')
    inlines = [CartItemInline]
    
    readonly_fields = ('total_subtotal', 'grand_total', 'created_at', 'updated_at')
