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


# DatalistInput Widget
class DatalistInput(forms.widgets.Input):
    input_type = 'text'
    template_name = 'django/forms/widgets/input.html' # Default, can be overridden

    def __init__(self, attrs=None, queryset=None):
        super().__init__(attrs)
        self.queryset = queryset if queryset is not None else Contact.objects.none()
        # Ensure a unique id for the datalist for each widget instance
        self.datalist_id = f"datalist__{forms.utils.uuid.uuid4().hex}"


    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Link input to datalist
        context['widget']['attrs']['list'] = self.datalist_id
        return context

    def render(self, name, value, attrs=None, renderer=None):
        # Render the input element
        input_html = super().render(name, value, attrs, renderer)

        # Render the datalist element
        datalist_html = f'<datalist id="{self.datalist_id}">'
        if self.queryset:
            for item in self.queryset:
                datalist_html += f'<option value="{item.name}"></option>'
        datalist_html += '</datalist>'

        return input_html + datalist_html


class TransactionForm(forms.ModelForm):
    transaction_type_selector = forms.ChoiceField(
        choices=Category.TYPE_CHOICES, 
        required=True, 
        label=_("Transaction Type"),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_transaction_type_selector_field'})
    )
    contact = forms.CharField(
        required=False, # Since Transaction.contact can be null
        label=_("Contact"),
        widget=DatalistInput(attrs={'class': 'form-control'}) # Using DatalistInput
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
            # 'contact' widget is now defined with the field itself.
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        # labels for 'contact' is now part of the CharField definition
        # labels = {
        # 'contact': _('Contact'),
        # }


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
            if len(assigned_safes_ids) == 1:
                self.fields['safe'].initial = assigned_safes_ids[0]
                self.fields['safe'].disabled = True
                self.fields['safe'].queryset = Safe.objects.filter(id=assigned_safes_ids[0])
            else:
                self.fields['safe'].queryset = Safe.objects.filter(id__in=assigned_safes_ids)
        else:
            self.fields['safe'].queryset = Safe.objects.all()
            
        self.fields['category'].queryset = Category.objects.none()
        self.fields['sub_category'].queryset = SubCategory.objects.none()
        # self.fields['contact'].queryset = Contact.objects.none() # Queryset is now on the widget

        # Initialize contact widget queryset
        self.fields['contact'].widget.queryset = Contact.objects.none()


        if self.instance and self.instance.pk and self.instance.category:
            self.fields['transaction_type_selector'].initial = self.instance.category.type
            self.fields['category'].queryset = Category.objects.filter(type=self.instance.category.type).order_by('name')
            if self.instance.sub_category:
                 self.fields['sub_category'].queryset = SubCategory.objects.filter(category=self.instance.category).order_by('name')
            
            # Update contact widget queryset and label based on instance category type
            current_contact_queryset = Contact.objects.none()
            if self.instance.category.type == Category.TRANSACTION_TYPE_INCOME:
                current_contact_queryset = Contact.objects.filter(customer=True).order_by('name')
                self.fields['contact'].label = _("Customer")
            elif self.instance.category.type == Category.TRANSACTION_TYPE_EXPENSE:
                current_contact_queryset = Contact.objects.filter(vendor=True).order_by('name')
                self.fields['contact'].label = _("Vendor")
            else:
                current_contact_queryset = Contact.objects.all().order_by('name')
            self.fields['contact'].widget.queryset = current_contact_queryset

            # Set initial value for contact field if instance has a contact
            if self.instance.contact:
                self.fields['contact'].initial = self.instance.contact.name


        if 'transaction_type_selector' in self.data:
            try:
                selected_type = self.data.get('transaction_type_selector')
                self.fields['category'].queryset = Category.objects.filter(type=selected_type).order_by('name')
                
                # Update contact widget queryset and label based on selected transaction type
                new_contact_queryset = Contact.objects.none()
                if selected_type == Category.TRANSACTION_TYPE_INCOME:
                    new_contact_queryset = Contact.objects.filter(customer=True).order_by('name')
                    self.fields['contact'].label = _("Customer")
                elif selected_type == Category.TRANSACTION_TYPE_EXPENSE:
                    new_contact_queryset = Contact.objects.filter(vendor=True).order_by('name')
                    self.fields['contact'].label = _("Vendor")
                else:
                    new_contact_queryset = Contact.objects.all().order_by('name')
                self.fields['contact'].widget.queryset = new_contact_queryset
            except (ValueError, TypeError):
                pass 
        
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['sub_category'].queryset = SubCategory.objects.filter(category_id=category_id).order_by('name')
            except (ValueError, TypeError):
                pass

    def clean_contact(self):
        contact_name = self.cleaned_data.get('contact')
        if not contact_name: # If contact is optional and not provided
            # Check if the model field allows blank
            model_field = Transaction._meta.get_field('contact')
            if model_field.blank:
                 return None # Return None if allowed to be blank/null
            else: # Should not happen if CharField(required=False)
                 raise forms.ValidationError(_("This field is required."), code='required')


        try:
            contact = Contact.objects.get(name=contact_name)
            return contact
        except Contact.DoesNotExist:
            raise forms.ValidationError(_("Contact not found. Please select from the list or ensure the contact exists."), code='invalid_contact')
        except Contact.MultipleObjectsReturned: # Should ideally not happen with unique names
            raise forms.ValidationError(_("Multiple contacts found with this name. Please refine."), code='multiple_contacts')


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

