# cashflow/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Transaction, Safe, Category, SubCategory, UserSafeAssignment, TransactionType
from django.contrib.auth.models import User

# Placeholder for contacts app Contact model
try:
    from contacts.models import Contact
except ImportError:
    class Contact(models.Model): # Placeholder
        name = models.CharField(max_length=255)
        CONTACT_TYPE_CHOICES = [
            ('CUSTOMER', _('Customer')),
            ('VENDOR', _('Vendor')),
            ('EMPLOYEE', _('Employee')),
            ('OTHER', _('Other')),
        ]
        contact_type = models.CharField(max_length=10, choices=CONTACT_TYPE_CHOICES, verbose_name=_("Contact Type"))
        def __str__(self):
            return self.name

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'transaction_date', 'safe', 'category', 'sub_category', 
            'amount', 'payment_method', 'contact', 'notes'
        ]
        widgets = {
            'transaction_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'safe': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'sub_category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'contact': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter safes based on user assignment if the user is not a superuser
        if user and not user.is_superuser:
            assigned_safes_ids = UserSafeAssignment.objects.filter(user=user).values_list('safe_id', flat=True)
            self.fields['safe'].queryset = Safe.objects.filter(id__in=assigned_safes_ids)
        else:
            self.fields['safe'].queryset = Safe.objects.all()
            
        self.fields['category'].queryset = Category.objects.none()
        self.fields['sub_category'].queryset = SubCategory.objects.none()

        if 'safe' in self.data:
            try:
                safe_id = int(self.data.get('safe'))
                # Potentially further filter categories if needed based on safe or other criteria
                # For now, all categories are available once a safe is chosen.
                # The main filtering for categories will be based on transaction_type, handled by JS.
            except (ValueError, TypeError):
                pass # invalid input from browser, ignore and fallback to empty.
        elif self.instance.pk and self.instance.safe:
             # Populate categories for existing instance
            pass # Will be handled by JS or view logic for initial population

        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['sub_category'].queryset = SubCategory.objects.filter(category_id=category_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.category:
            self.fields['sub_category'].queryset = self.instance.category.subcategories.order_by('name')
        
        # Dynamic filtering for contacts based on transaction type (selected category's type)
        # This is more complex and typically handled with JavaScript calling a view.
        # For now, showing all contacts.
        self.fields['contact'].queryset = Contact.objects.all().order_by('name')
        self.fields['contact'].label = _("العميل/المورد") # Generic label

# --- Forms for Superuser Configuration ---

class SafeForm(forms.ModelForm):
    class Meta:
        model = Safe
        fields = ['name'] # Balance is managed by transactions
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class TransactionTypeForm(forms.ModelForm):
    class Meta:
        model = TransactionType
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'transaction_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
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
        self.fields['category'].queryset = Category.objects.all().select_related('transaction_type').order_by('transaction_type__name', 'name')


class UserSafeAssignmentForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True).order_by('username'), widget=forms.Select(attrs={'class': 'form-select'}))
    safe = forms.ModelChoiceField(queryset=Safe.objects.all().order_by('name'), widget=forms.Select(attrs={'class': 'form-select'}))
    
    class Meta:
        model = UserSafeAssignment
        fields = ['user', 'safe']

