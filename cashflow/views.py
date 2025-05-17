# cashflow/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
from django.db import models #  <--- IMPORTED models HERE

from .models import Transaction, Safe, Category, SubCategory, UserSafeAssignment, TransactionType
from .forms import TransactionForm, SafeForm, CategoryForm, SubCategoryForm, UserSafeAssignmentForm, TransactionTypeForm

# Assuming your contacts app and Contact model are defined
try:
    from contacts.models import Contact
except ImportError:
    # This is a placeholder. In a real project, ensure this model is correctly imported
    # or that the contacts app is properly installed and configured.
    class Contact(models.Model): 
        name = models.CharField(max_length=255, verbose_name=_("Name"))
        CONTACT_TYPE_CHOICES = [
            ('CUSTOMER', _('Customer')),
            ('VENDOR', _('Vendor')),
            ('EMPLOYEE', _('Employee')),
            ('OTHER', _('Other')),
        ]
        contact_type = models.CharField(
            max_length=10, 
            choices=CONTACT_TYPE_CHOICES, 
            verbose_name=_("Contact Type")
        )

        def __str__(self):
            return self.name
        
        class Meta:
            verbose_name = _("Contact")
            verbose_name_plural = _("Contacts")


# --- Helper Functions ---
def is_superuser(user):
    """Checks if the user is a superuser."""
    return user.is_superuser

def get_user_safes(user):
    """Returns a queryset of safes assigned to the user."""
    if user.is_superuser:
        return Safe.objects.all()
    # Ensure related_name 'user_assignments' on Safe model points to UserSafeAssignment
    return Safe.objects.filter(user_assignments__user=user)

def get_user_total_balance(user):
    """Calculates the total balance across all safes assigned to the user."""
    safes = get_user_safes(user)
    # Ensure 'balance' is a field on the Safe model
    total_balance = safes.aggregate(total=models.Sum('balance'))['total'] or Decimal('0.00')
    return total_balance

# --- Transaction Views ---
@login_required
def transaction_list_view(request):
    user_safes = get_user_safes(request.user)
    transactions = Transaction.objects.filter(safe__in=user_safes).select_related(
        'safe', 'category', 'category__transaction_type', 'sub_category', 'user', 'contact'
    ).order_by('-transaction_date', '-created_at')
    
    total_balance = get_user_total_balance(request.user)
    
    context = {
        'transactions': transactions,
        'page_title': _('All Transactions'),
        'total_balance': total_balance,
        'user_safes': user_safes, 
    }
    return render(request, 'cashflow/transaction_list.html', context)

@login_required
def today_transactions_view(request):
    user_safes = get_user_safes(request.user)
    today_min = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_max = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    transactions = Transaction.objects.filter(
        safe__in=user_safes,
        transaction_date__range=(today_min, today_max)
    ).select_related(
        'safe', 'category', 'category__transaction_type', 'sub_category', 'user', 'contact'
    ).order_by('-transaction_date', '-created_at')
    
    total_balance = get_user_total_balance(request.user)

    # Calculate today's net flow
    # Ensure TransactionType names are consistent with your data/translations
    today_income = transactions.filter(
        category__transaction_type__name__in=[_('Income'), _('Internal Transfer In')]
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    
    today_expense = transactions.filter(
        category__transaction_type__name__in=[_('Expense'), _('Internal Transfer Out')]
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    
    today_net_flow = today_income - today_expense

    context = {
        'transactions': transactions,
        'page_title': _("Today's Transactions"),
        'total_balance': total_balance,
        'today_net_flow': today_net_flow,
        'user_safes': user_safes,
    }
    return render(request, 'cashflow/transaction_list.html', context)

@login_required
def transaction_create_view(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user 
            transaction.save()
            return redirect('cashflow:transaction_list')
    else:
        form = TransactionForm(user=request.user)
    
    transaction_types = TransactionType.objects.all()

    context = {
        'form': form,
        'page_title': _('New Transaction'),
        'transaction_types_for_js': transaction_types,
    }
    return render(request, 'cashflow/transaction_form.html', context)

@login_required
def transaction_update_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    user_safes = get_user_safes(request.user)

    if transaction.safe not in user_safes and not request.user.is_superuser:
        return redirect('cashflow:transaction_list') 

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('cashflow:transaction_list')
    else:
        form = TransactionForm(instance=transaction, user=request.user)

    transaction_types = TransactionType.objects.all()
    context = {
        'form': form,
        'transaction': transaction,
        'page_title': _('Edit Transaction'),
        'transaction_types_for_js': transaction_types,
    }
    return render(request, 'cashflow/transaction_form.html', context)

@login_required
def transaction_delete_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    user_safes = get_user_safes(request.user)

    if transaction.safe not in user_safes and not request.user.is_superuser:
        return redirect('cashflow:transaction_list')

    if request.method == 'POST':
        transaction.delete()
        return redirect('cashflow:transaction_list')
    context = {
        'transaction': transaction,
        'page_title': _('Delete Transaction'),
    }
    return render(request, 'cashflow/transaction_confirm_delete.html', context)


# --- AJAX Views for Dynamic Form Filtering ---
@login_required
def ajax_load_categories(request):
    transaction_type_id = request.GET.get('transaction_type_id')
    if transaction_type_id:
        try:
            # Ensure transaction_type_id is a valid integer
            transaction_type_id = int(transaction_type_id)
            categories = Category.objects.filter(transaction_type_id=transaction_type_id).order_by('name')
            return JsonResponse(list(categories.values('id', 'name')), safe=False)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid transaction_type_id'}, status=400)
    return JsonResponse([], safe=False)

@login_required
def ajax_load_subcategories(request):
    category_id = request.GET.get('category_id')
    if category_id:
        try:
            # Ensure category_id is a valid integer
            category_id = int(category_id)
            subcategories = SubCategory.objects.filter(category_id=category_id).order_by('name')
            return JsonResponse(list(subcategories.values('id', 'name')), safe=False)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid category_id'}, status=400)
    return JsonResponse([], safe=False)

@login_required
def ajax_load_contacts(request):
    category_id = request.GET.get('category_id')
    contacts_qs = Contact.objects.all()
    if category_id:
        try:
            category = Category.objects.select_related('transaction_type').get(id=int(category_id))
            # Ensure your TransactionType names used for filtering are accurate
            # It's more robust to use a specific field like 'code' or 'effect' on TransactionType
            # rather than relying on translated names.
            if category.transaction_type.name == _('Income'): 
                contacts_qs = Contact.objects.filter(contact_type='CUSTOMER')
            elif category.transaction_type.name == _('Expense'):
                contacts_qs = Contact.objects.filter(contact_type='VENDOR')
            # Add more conditions if needed for 'Internal Transfer' etc.
        except (Category.DoesNotExist, ValueError, TypeError):
            # Fallback to all contacts if category is invalid or not found
            pass 
            
    contacts = list(contacts_qs.values('id', 'name'))
    return JsonResponse(contacts, safe=False)


# --- Superuser Configuration Views ---
class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to ensure the user is a superuser."""
    def test_func(self):
        return self.request.user.is_superuser

@login_required
@user_passes_test(is_superuser)
def config_dashboard_view(request):
    context = {'page_title': _('Configuration Dashboard')}
    return render(request, 'cashflow/config_dashboard.html', context)

# Safes
class SafeListView(SuperuserRequiredMixin, ListView):
    model = Safe
    template_name = 'cashflow/config/safe_list.html'
    context_object_name = 'safes'
    paginate_by = 10

class SafeCreateView(SuperuserRequiredMixin, CreateView):
    model = Safe
    form_class = SafeForm
    template_name = 'cashflow/config/safe_form.html'
    success_url = reverse_lazy('cashflow:safe_list')
    extra_context = {'page_title': _('Create Safe')}

class SafeUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Safe
    form_class = SafeForm
    template_name = 'cashflow/config/safe_form.html'
    success_url = reverse_lazy('cashflow:safe_list')
    extra_context = {'page_title': _('Update Safe')}

class SafeDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Safe
    template_name = 'cashflow/config/confirm_delete.html'
    success_url = reverse_lazy('cashflow:safe_list')
    extra_context = {'object_type': _('Safe')}


# Transaction Types
class TransactionTypeListView(SuperuserRequiredMixin, ListView):
    model = TransactionType
    template_name = 'cashflow/config/transactiontype_list.html'
    context_object_name = 'transaction_types'
    paginate_by = 10

class TransactionTypeCreateView(SuperuserRequiredMixin, CreateView):
    model = TransactionType
    form_class = TransactionTypeForm
    template_name = 'cashflow/config/transactiontype_form.html'
    success_url = reverse_lazy('cashflow:transaction_type_list')
    extra_context = {'page_title': _('Create Transaction Type')}

class TransactionTypeUpdateView(SuperuserRequiredMixin, UpdateView):
    model = TransactionType
    form_class = TransactionTypeForm
    template_name = 'cashflow/config/transactiontype_form.html'
    success_url = reverse_lazy('cashflow:transaction_type_list')
    extra_context = {'page_title': _('Update Transaction Type')}

class TransactionTypeDeleteView(SuperuserRequiredMixin, DeleteView):
    model = TransactionType
    template_name = 'cashflow/config/confirm_delete.html'
    success_url = reverse_lazy('cashflow:transaction_type_list')
    extra_context = {'object_type': _('Transaction Type')}


# Categories
class CategoryListView(SuperuserRequiredMixin, ListView):
    model = Category
    template_name = 'cashflow/config/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

class CategoryCreateView(SuperuserRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'cashflow/config/category_form.html'
    success_url = reverse_lazy('cashflow:category_list')
    extra_context = {'page_title': _('Create Category')}

class CategoryUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'cashflow/config/category_form.html'
    success_url = reverse_lazy('cashflow:category_list')
    extra_context = {'page_title': _('Update Category')}

class CategoryDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Category
    template_name = 'cashflow/config/confirm_delete.html'
    success_url = reverse_lazy('cashflow:category_list')
    extra_context = {'object_type': _('Category')}


# SubCategories
class SubCategoryListView(SuperuserRequiredMixin, ListView):
    model = SubCategory
    template_name = 'cashflow/config/subcategory_list.html'
    context_object_name = 'subcategories'
    paginate_by = 10

class SubCategoryCreateView(SuperuserRequiredMixin, CreateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = 'cashflow/config/subcategory_form.html'
    success_url = reverse_lazy('cashflow:subcategory_list')
    extra_context = {'page_title': _('Create SubCategory')}

class SubCategoryUpdateView(SuperuserRequiredMixin, UpdateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = 'cashflow/config/subcategory_form.html'
    success_url = reverse_lazy('cashflow:subcategory_list')
    extra_context = {'page_title': _('Update SubCategory')}

class SubCategoryDeleteView(SuperuserRequiredMixin, DeleteView):
    model = SubCategory
    template_name = 'cashflow/config/confirm_delete.html'
    success_url = reverse_lazy('cashflow:subcategory_list')
    extra_context = {'object_type': _('SubCategory')}


# UserSafeAssignment
class UserSafeAssignmentListView(SuperuserRequiredMixin, ListView):
    model = UserSafeAssignment
    template_name = 'cashflow/config/usersafeassignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 10

class UserSafeAssignmentCreateView(SuperuserRequiredMixin, CreateView):
    model = UserSafeAssignment
    form_class = UserSafeAssignmentForm
    template_name = 'cashflow/config/usersafeassignment_form.html'
    success_url = reverse_lazy('cashflow:usersafeassignment_list')
    extra_context = {'page_title': _('Assign Safe to User')}

class UserSafeAssignmentDeleteView(SuperuserRequiredMixin, DeleteView):
    model = UserSafeAssignment
    template_name = 'cashflow/config/confirm_delete.html' 
    success_url = reverse_lazy('cashflow:usersafeassignment_list')
    extra_context = {'object_type': _('Safe Assignment')}
