from django import forms
from .models import Contact

class ContactForm(forms.ModelForm):
    PROVINCES = [
        ("الإسكندرية", "الإسكندرية"),
        ("الإسماعيلية", "الإسماعيلية"),
        ("أسوان", "أسوان"),
        ("أسيوط", "أسيوط"),
        ("الأقصر", "الأقصر"),
        ("البحر الأحمر", "البحر الأحمر"),
        ("البحيرة", "البحيرة"),
        ("بني سويف", "بني سويف"),
        ("بورسعيد", "بورسعيد"),
        ("جنوب سيناء", "جنوب سيناء"),
        ("الجيزة", "الجيزة"),
        ("الدقهلية", "الدقهلية"),
        ("دمياط", "دمياط"),
        ("سوهاج", "سوهاج"),
        ("السويس", "السويس"),
        ("الشرقية", "الشرقية"),
        ("شمال سيناء", "شمال سيناء"),
        ("الغربية", "الغربية"),
        ("الفيوم", "الفيوم"),
        ("القاهرة", "القاهرة"),
        ("القليوبية", "القليوبية"),
        ("قنا", "قنا"),
        ("كفر الشيخ", "كفر الشيخ"),
        ("مطروح", "مطروح"),
        ("المنوفية", "المنوفية"),
        ("المنيا", "المنيا"),
        ("الوادي الجديد", "الوادي الجديد"),
    ]
    
    province = forms.ChoiceField(
        choices=PROVINCES,
        widget=forms.TextInput(attrs={'list': 'ProvinceList'})
    )
    
    class Meta:
        model = Contact
        fields = [
            'name', 'phone1', 'phone2', 'customer', 'vendor', 
            'address1', 'address2', 'city', 'province', 
            'price_list', 'discount', 'shipping_cost', 'payment_method', 'details'
        ]
        widgets = {
            'details': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Skip checkboxes or other widgets that don't require form-control styling
            if not isinstance(field.widget, forms.CheckboxInput):
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = (existing_classes + ' form-control').strip()

