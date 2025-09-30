from django.contrib import admin
from .models import Promotion 

# --- Promotion Admin ---
@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    # ปรับปรุง list_display ให้ตรงกับชื่อฟิลด์จริง
    # ฟิลด์ 'description' และ 'start_date'/'end_date' ถูกเปลี่ยนชื่อ/ลบออก
    list_display = (
        'code', 
        'get_discount_display', # ฟังก์ชันแสดงผลส่วนลด
        'discount_type', 
        'is_active', 
        'valid_from', # ชื่อฟิลด์จริง
        'valid_to' # ชื่อฟิลด์จริง
    )
    
    # ปรับปรุง list_filter ให้ตรงกับชื่อฟิลด์จริง
    list_filter = ('is_active', 'discount_type', 'valid_from', 'valid_to')
    
    search_fields = ('code',)
    
    # ลบ filter_horizontal ออก เนื่องจากโมเดล Promotion ไม่มีฟิลด์ M2M กับ Product
    # filter_horizontal = ('products',) 

    # เพิ่มเมธอดเพื่อแสดงผลส่วนลดใน list_display แทนฟิลด์ description
    def get_discount_display(self, obj):
        if obj.discount_type == 'PERCENT':
            return f"{obj.discount_value} %"
        return f"{obj.discount_value:,.2f} บาท"
    get_discount_display.short_description = 'ส่วนลด'
