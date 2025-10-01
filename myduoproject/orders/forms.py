# orders/forms.py
from django import forms
# สมมติว่า PaymentMethod คือ Choices field หรือ Enum ที่คุณใช้
from .models import PaymentMethod 

class CheckoutForm(forms.Form):
    """
    Form สำหรับรวบรวมข้อมูลผู้รับ ที่อยู่จัดส่ง และหลักฐานการชำระเงิน
    """
    # 1. ข้อมูลผู้รับ
    full_name = forms.CharField(label='ชื่อ-นามสกุล', max_length=255, required=True)
    email = forms.EmailField(label='อีเมล', max_length=255, required=True)
    phone_number = forms.CharField(label='เบอร์โทรศัพท์', max_length=20, required=True)
    shipping_address = forms.CharField(label='ที่อยู่จัดส่ง', widget=forms.Textarea(attrs={'rows': 3}), required=True)

    # 2. วิธีการชำระเงิน
    payment_method = forms.ChoiceField(
        label='ช่องทางการชำระเงิน',
        choices=PaymentMethod.choices,
        widget=forms.RadioSelect,
        required=True
    )
    
    # 3. ฟิลด์สำหรับอัปโหลดสลิปการโอนเงิน (ใช้ FileField)
    # เราตั้งค่า required=False ในฟอร์ม เพราะมันจะถูกบังคับในเมธอด clean() แทน
    payment_slip = forms.FileField(
        label='อัปโหลดสลิปหลักฐานการโอนเงิน',
        required=False, 
        widget=forms.FileInput(attrs={'accept': 'image/*,application/pdf'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # เพิ่ม Tailwind classes ให้กับทุกฟิลด์เพื่อความสวยงาม
        tailwind_class = 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'
        
        for name, field in self.fields.items():
            if name != 'payment_method' and name != 'payment_slip': # ยกเว้น RadioSelect และ FileInput
                field.widget.attrs.update({'class': tailwind_class})
            
            # จัดการ class สำหรับ File Input ให้ดูดี
            if name == 'payment_slip':
                 field.widget.attrs.update({'class': 'w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none'})

    def clean(self):
        """
        ตรวจสอบเงื่อนไข: หากเลือก 'โอนเงินผ่านธนาคาร' ต้องมีไฟล์สลิป
        """
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        payment_slip = cleaned_data.get('payment_slip')
        
        # สมมติว่าค่าสำหรับ 'โอนเงินผ่านธนาคาร' คือ 'Transfer'
        # คุณต้องตรวจสอบกับค่าจริงใน PaymentMethod.choices ของคุณ
        if payment_method == 'Transfer' and not payment_slip:
            self.add_error('payment_slip', 'กรุณาอัปโหลดสลิปหลักฐานการโอนเงิน เมื่อเลือกช่องทางนี้')
            
        return cleaned_data
