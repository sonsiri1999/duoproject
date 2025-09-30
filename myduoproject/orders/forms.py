from django import forms
from .models import PaymentMethod

class CheckoutForm(forms.Form):
    """
    Form สำหรับรวบรวมข้อมูลผู้รับและที่อยู่จัดส่งในหน้า Checkout
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # เพิ่ม Tailwind classes ให้กับทุกฟิลด์เพื่อความสวยงาม
        tailwind_class = 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'
        
        for name, field in self.fields.items():
            if name != 'payment_method': # ยกเว้น RadioSelect
                field.widget.attrs.update({'class': tailwind_class})
