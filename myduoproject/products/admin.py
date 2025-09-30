from django.contrib import admin
from .models import Product, ProductVariant, Category, Brand # 1. เพิ่ม Category และ Brand

# --- ProductVariant Inline Admin ---
class ProductVariantInline(admin.TabularInline):
    # เชื่อมกับ ProductVariant
    model = ProductVariant
    # ฟิลด์ที่ต้องการแสดงใน Inline
    fields = ('size', 'original_price', 'current_price', 'stock', 'is_default') 
    extra = 1

# --- Product Admin ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # แก้ไข list_display: ลบ 'estimated_delivery' ออก 
    # และใช้ 'created_at' แทน (ถ้าต้องการแสดงวันที่)
    list_display = (
        'name', 
        'status', 
        'category', # เพิ่ม category เพื่อให้กรองง่ายขึ้น
        'get_min_price', # ฟังก์ชันแสดงราคาต่ำสุด
        'is_featured'
    )
    
    # แก้ไข list_filter: ลบ 'estimated_delivery' ออก 
    list_filter = ('status', 'is_featured', 'category', 'brand')
    
    # fields ที่จะแสดงในหน้าเพิ่ม/แก้ไข
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'image', 'sku', 'status', 'is_featured')
        }),
        ('Relationship', {
            'fields': ('category', 'brand',)
        }),
    )
    
    search_fields = ('name', 'description', 'sku')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]
    
    # ฟังก์ชันคำนวณราคาเริ่มต้น (ราคาต่ำสุดของ Variants ที่มีสต็อก)
    def get_min_price(self, obj):
        # ดึงราคาต่ำสุดจาก variants ทั้งหมดที่มีสต็อก > 0
        min_price = obj.variants.filter(stock__gt=0).order_by('current_price').values_list('current_price', flat=True).first()
        return f"฿ {min_price:,.2f}" if min_price is not None else "N/A"
    get_min_price.short_description = 'เริ่มต้นที่'


# --- 2. Register Helper Models ---

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category model."""
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Admin configuration for Brand model."""
    list_display = ('name',)
    search_fields = ('name',)
