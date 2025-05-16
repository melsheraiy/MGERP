from django import forms
from .models import SparePartRequest, Category
from django.utils.translation import gettext_lazy as _

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter category name')}),
        }
        labels = {
            'name': _('Category Name'),
        }

class SparePartRequestForm(forms.ModelForm):
    # Field for removing photo during edit
    remove_photo = forms.BooleanField(required=False, label=_("Remove current photo"), widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = SparePartRequest
        fields = [
            'category', 'description', 'requested_qty', 'unit',
            'notes', 'photo', 'remove_photo' # remove_photo is not a model field, handled in view
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'required': 'required'}),
            'requested_qty': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': 'any', 'required': 'required'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
        labels = {
            'category': _('Category *'),
            'description': _('Spare Part Description *'),
            'requested_qty': _('Requested Quantity *'),
            'unit': _('Unit *'),
            'notes': _('Additional Notes'),
            'photo': _('Spare Part Photo (Optional)'),
        }
        help_texts = {
            'photo': _('Max file size 5MB. Accepted formats: JPG, PNG, GIF.'),
        }


    def __init__(self, *args, **kwargs):
        # user_profile = kwargs.pop('user_profile', None) # For sector-specific categories if needed
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['category'].empty_label = _("Select Category...")
        self.fields['unit'].empty_label = _("Select Unit...")

        # If editing, 'remove_photo' is only relevant if there's an existing photo
        if self.instance and not self.instance.photo:
            if 'remove_photo' in self.fields:
                 del self.fields['remove_photo'] # Or hide it: self.fields['remove_photo'].widget = forms.HiddenInput()
        elif 'remove_photo' not in self.fields and self.instance and self.instance.photo :
            # This case should not happen if field is defined in Meta, but as a safeguard:
            self.fields['remove_photo'] = forms.BooleanField(required=False, label=_("Remove current photo"))


class SupervisorSparePartEditForm(SparePartRequestForm):
    """
    A form for supervisors to edit requests, potentially including status and received_qty.
    This extends the base form.
    """
    status = forms.ChoiceField(choices=SparePartRequest.STATUS_CHOICES, required=True, widget=forms.Select(attrs={'class': 'form-control'}), label=_("Status Update (Supervisor)"))
    received_qty_form_input = forms.DecimalField(required=False, label=_("Received Quantity (when status is 'Received')"), min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}))

    class Meta(SparePartRequestForm.Meta):
        fields = SparePartRequestForm.Meta.fields + ['status', 'received_qty_form_input']
        # No need to redefine widgets if they are inherited correctly or if new ones are fine with defaults.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing and status is 'Received', make received_qty_form_input required or prefill
        if self.instance and self.instance.pk:
            self.fields['status'].initial = self.instance.status
            if self.instance.status == SparePartRequest.STATUS_RECEIVED:
                self.fields['received_qty_form_input'].initial = self.instance.received_qty
                self.fields['received_qty_form_input'].required = True # Make it required if status is received
            else:
                self.fields['received_qty_form_input'].required = False


    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        received_qty_form_input = cleaned_data.get('received_qty_form_input')

        if status == SparePartRequest.STATUS_RECEIVED:
            if received_qty_form_input is None or received_qty_form_input < 0:
                self.add_error('received_qty_form_input', _("Received quantity is required and must be positive when status is 'Received'."))
        return cleaned_data


class SupervisorConfirmOrderForm(forms.Form):
    ordered_qty = forms.DecimalField(label=_("Confirmed Order Quantity"), min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'required': 'required'}))

class UserConfirmReceptionForm(forms.Form):
    received_qty = forms.DecimalField(label=_("Actual Received Quantity"), min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'required': 'required'}))

