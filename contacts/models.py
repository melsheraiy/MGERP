from django.db import models

class Contact(models.Model):
    name = models.CharField("الاسم", max_length=255)
    phone1 = models.CharField("الهاتف ١", max_length=11)
    phone2 = models.CharField("الهاتف ٢", max_length=11, blank=True, null=True)
    customer = models.BooleanField("عميل", default=False)
    vendor = models.BooleanField("مورد", default=False)
    address1 = models.CharField("العنوان ١", max_length=255, blank=True, null=True)
    address2 = models.CharField("العنوان ٢", max_length=255, blank=True, null=True)
    city = models.CharField("المدينة", max_length=100)
    province = models.CharField("المحافظة", max_length=100)
    price_list = models.PositiveIntegerField("قائمة الأسعار")
    discount = models.DecimalField("الخصم", max_digits=4, decimal_places=1, default=0)
    shipping_cost = models.DecimalField("تكلفة الشحن", max_digits=10, decimal_places=2, default=0)
    PAYMENT_METHOD_CHOICES = [
        ('فورى', 'فورى'),
        ('شيكات', 'شيكات'),
        ('دفعات', 'دفعات'),
    ]
    payment_method = models.CharField("طريقة الدفع", max_length=50,
                                      choices=PAYMENT_METHOD_CHOICES,
                                      blank=False)
    details = models.TextField("تفاصيل", blank=True, null=True)
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)


    def __str__(self):
        return self.name
