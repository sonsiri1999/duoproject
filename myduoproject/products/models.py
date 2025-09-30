from django.db import models
from django.utils.text import slugify

# ----------------------------------------------------------------------
# Helper Models (Category and Brand)
# ----------------------------------------------------------------------

class Category(models.Model):
    """
    หมวดหมู่สำหรับจัดกลุ่มสินค้า
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อหมวดหมู่")
    slug = models.SlugField(unique=True, max_length=100, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        verbose_name = "Category"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Brand(models.Model):
    """
    แบรนด์หรือผู้ผลิตสินค้า
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อแบรนด์")

    class Meta:
        verbose_name_plural = "Brands"
        verbose_name = "Brand"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    
# ----------------------------------------------------------------------
# Core Product Model
# ----------------------------------------------------------------------

class Product(models.Model):
    """
    โมเดลหลักสำหรับสินค้า
    """
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('PRE_ORDER', 'Pre-order'),
        ('DISCONTINUED', 'Discontinued'),
    ]
    
    name = models.CharField(max_length=255, verbose_name="ชื่อสินค้า")
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    description = models.TextField(verbose_name="รายละเอียดสินค้า")
    
    # Foreign Keys
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, related_name='products', verbose_name="หมวดหมู่")
    brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, null=True, related_name='products', verbose_name="แบรนด์")
    
    # Metadata and status
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="SKU หลัก")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE', verbose_name="สถานะสินค้า")
    is_featured = models.BooleanField(default=False, verbose_name="สินค้าแนะนำ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Image (requires django-pillow installed)
    image = models.ImageField(upload_to='products/%Y/%m/', blank=True, null=True, verbose_name="รูปภาพหลัก")

    class Meta:
        verbose_name_plural = "Products"
        verbose_name = "Product"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# ----------------------------------------------------------------------
# Product Variants Model
# ----------------------------------------------------------------------

class ProductVariant(models.Model):
    """
    โมเดลสำหรับตัวเลือกสินค้า (เช่น ขนาด สี หรือรูปแบบอื่น ๆ)
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants', verbose_name="สินค้า")
    size = models.CharField(max_length=50, verbose_name="ขนาด/ตัวเลือก") # เช่น S, M, L หรือ สีแดง, สีฟ้า
    original_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาปกติ")
    current_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาขายปัจจุบัน")
    stock = models.IntegerField(default=0, verbose_name="จำนวนในสต็อก")
    is_default = models.BooleanField(default=False, verbose_name="ตัวเลือกหลัก")
    
    class Meta:
        verbose_name_plural = "Product Variants"
        verbose_name = "Product Variant"
        # ทำให้ไม่สามารถมีตัวเลือก (size) ซ้ำกันในสินค้าเดียวกันได้
        unique_together = ('product', 'size') 

    def __str__(self):
        return f"{self.product.name} - {self.size}"
