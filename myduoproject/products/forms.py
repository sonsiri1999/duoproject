from django import forms
from .models import Product, ProductVariant, Category, Brand

class ProductCreateForm(forms.ModelForm):
    """
    Form for creating a new Product and its default ProductVariant simultaneously.
    """
    # Fields from Product Model
    name = forms.CharField(label='ชื่อสินค้า', max_length=255)
    description = forms.CharField(label='รายละเอียดสินค้า', widget=forms.Textarea(attrs={'rows': 4}))
    category = forms.ModelChoiceField(queryset=Category.objects.all(), label='หมวดหมู่')
    brand = forms.ModelChoiceField(queryset=Brand.objects.all(), label='แบรนด์')
    sku = forms.CharField(label='SKU (รหัสสินค้า)', max_length=50, required=False)
    image = forms.ImageField(label='รูปภาพหลัก', required=False) # Requires Pillow

    # Fields for the default ProductVariant
    variant_size = forms.CharField(label='ขนาด/ตัวเลือกหลัก (เช่น S, 500g)', max_length=50)
    original_price = forms.DecimalField(label='ราคาปกติ', min_value=0)
    current_price = forms.DecimalField(label='ราคาขายปัจจุบัน', min_value=0)
    stock = forms.IntegerField(label='จำนวนในสต็อก', min_value=0)

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'brand', 'sku', 'image']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Tailwind classes to all fields
        tailwind_class = 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'
        
        for name, field in self.fields.items():
            if name != 'image': # Image field doesn't need text input styling
                field.widget.attrs.update({'class': tailwind_class})
            
            if name == 'description':
                field.widget.attrs.update({'class': f'{tailwind_class} h-24'}) # Make textarea taller
            
            if name in ['original_price', 'current_price', 'stock']:
                # For numerical/smaller inputs, we can keep them full width or customize if needed
                field.widget.attrs.update({'class': tailwind_class})

    def save(self, commit=True):
        # 1. Save the Product instance
        product = super().save(commit=False)
        
        if commit:
            product.save()
            
            # 2. Create the default ProductVariant
            ProductVariant.objects.create(
                product=product,
                size=self.cleaned_data['variant_size'],
                original_price=self.cleaned_data['original_price'],
                current_price=self.cleaned_data['current_price'],
                stock=self.cleaned_data['stock'],
                is_default=True,
            )
        
        return product
