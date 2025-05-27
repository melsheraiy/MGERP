# cashflow/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db import models # <--- IMPORTED models HERE
from .models import Transaction, Safe, Category, SubCategory, UserSafeAssignment # TransactionType removed
from django.contrib.auth.models import User

# Placeholder for contacts app Contact model
try:
    from contacts.models import Contact as ActualContact
    # Check if the actual Contact model has 'customer' and 'vendor' fields
    # This is a simplified check; you might need a more robust way if attributes can be None
    contact_fields = [field.name for field in ActualContact._meta.get_fields()]
    if 'customer' not in contact_fields or 'vendor' not in contact_fields:
        # If actual Contact model exists but lacks these specific boolean fields,
        # this proxy model attempts to add them. This might not be the ideal permanent solution;
        # ideally, the main contacts.models.Contact would be adjusted.
        class Contact(ActualContact):
            # Assuming these are the correct field names in your actual Contact model
            customer = models.BooleanField(default=False, verbose_name=_("Customer"))
            vendor = models.BooleanField(default=False, verbose_name=_("Vendor"))
            class Meta:
                proxy = True 
    else:
        Contact = ActualContact
except ImportError:
    # This placeholder is used if 'contacts.models' cannot be imported at all.
    class Contact(models.Model): 
        name = models.CharField(max_length=255, verbose_name=_("Name"))
        customer = models.BooleanField(default=False, verbose_name=_("Customer")) # Corrected field name
        vendor = models.BooleanField(default=False, verbose_name=_("Vendor"))   # Corrected field name
        # You might have other fields like email, phone, etc.

        def __str__(self):
            return self.name
        class Meta:
            verbose_name = _("Contact")
            verbose_name_plural = _("Contacts")


class TransactionForm(forms.ModelForm):
    transaction_type_selector = forms.ChoiceField(
        choices=Category.TYPE_CHOICES, 
        required=True, 
        label=_("Transaction Type"),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_transaction_type_selector_field'})
    )

    class Meta:
        model = Transaction
        fields = [
            'safe', 
            'category', 'sub_category', 
            'amount', 'payment_method', 'contact', 'notes'
        ]
        widgets = {
            'safe': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'sub_category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'contact': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'contact': _('Contact'), 
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Order fields to place transaction_type_selector before category
        field_order = [
            'safe', 'transaction_type_selector', 'category', 'sub_category',
            'amount', 'payment_method', 'contact', 'notes'
        ]
        self.order_fields(field_order)


        if user and not user.is_superuser:
            assigned_safes_ids = UserSafeAssignment.objects.filter(user=user).values_list('safe_id', flat=True)
            self.fields['safe'].queryset = Safe.objects.filter(id__in=assigned_safes_ids)
        else:
            self.fields['safe'].queryset = Safe.objects.all()
            
        self.fields['category'].queryset = Category.objects.none()
        self.fields['sub_category'].queryset = SubCategory.objects.none()
        self.fields['contact'].queryset = Contact.objects.none()

        if self.instance and self.instance.pk and self.instance.category:
            self.fields['transaction_type_selector'].initial = self.instance.category.type
            self.fields['category'].queryset = Category.objects.filter(type=self.instance.category.type).order_by('name')
            if self.instance.sub_category:
                 self.fields['sub_category'].queryset = SubCategory.objects.filter(category=self.instance.category).order_by('name')
            
            if self.instance.category.type == Category.TRANSACTION_TYPE_INCOME:
                self.fields['contact'].queryset = Contact.objects.filter(customer=True).order_by('name') # Corrected field
                self.fields['contact'].label = _("Customer")
            elif self.instance.category.type == Category.TRANSACTION_TYPE_EXPENSE:
                self.fields['contact'].queryset = Contact.objects.filter(vendor=True).order_by('name') # Corrected field
                self.fields['contact'].label = _("Vendor")
            else:
                self.fields['contact'].queryset = Contact.objects.all().order_by('name')

        if 'transaction_type_selector' in self.data:
            try:
                selected_type = self.data.get('transaction_type_selector')
                self.fields['category'].queryset = Category.objects.filter(type=selected_type).order_by('name')
                
                if selected_type == Category.TRANSACTION_TYPE_INCOME:
                    self.fields['contact'].queryset = Contact.objects.filter(customer=True).order_by('name') # Corrected
                    self.fields['contact'].label = _("Customer")
                elif selected_type == Category.TRANSACTION_TYPE_EXPENSE:
                    self.fields['contact'].queryset = Contact.objects.filter(vendor=True).order_by('name') # Corrected
                    self.fields['contact'].label = _("Vendor")
                else:
                    self.fields['contact'].queryset = Contact.objects.all().order_by('name')
            except (ValueError, TypeError):
                pass 
        
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['sub_category'].queryset = SubCategory.objects.filter(category_id=category_id).order_by('name')
            except (ValueError, TypeError):
                pass

# --- Forms for Superuser Configuration ---

class SafeForm(forms.ModelForm):
    class Meta:
        model = Safe
        fields = ['name'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
        }

class SubCategoryForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ['name', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('type', 'name')
        self.fields['category'].label_from_instance = lambda obj: f"{obj.get_type_display()} - {obj.name}"


class UserSafeAssignmentForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True).order_by('username'), widget=forms.Select(attrs={'class': 'form-select'}))
    safe = forms.ModelChoiceField(queryset=Safe.objects.all().order_by('name'), widget=forms.Select(attrs={'class': 'form-select'}))
    
    class Meta:
        model = UserSafeAssignment
        fields = ['user', 'safe']

