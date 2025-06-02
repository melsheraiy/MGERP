# cashflow/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
from django.db import models 
from django.db.models import Q

from .models import Transaction, Safe, Category, SubCategory, UserSafeAssignment # TransactionType removed
from .forms import TransactionForm, SafeForm, CategoryForm, SubCategoryForm, UserSafeAssignmentForm # TransactionTypeForm removed

# Placeholder for contacts app Contact model
try:
    from contacts.models import Contact as ActualContact
    contact_fields = [field.name for field in ActualContact._meta.get_fields()]
    if 'customer' not in contact_fields or 'vendor' not in contact_fields:
        class Contact(ActualContact):
            customer = models.BooleanField(default=False, verbose_name=_("Customer")) # Corrected
            vendor = models.BooleanField(default=False, verbose_name=_("Vendor"))     # Corrected
            class Meta:
                proxy = True 
    else:
        Contact = ActualContact
except ImportError:
    class Contact(models.Model): 
        name = models.CharField(max_length=255, verbose_name=_("Name"))
        customer = models.BooleanField(default=False, verbose_name=_("Customer")) # Corrected
        vendor = models.BooleanField(default=False, verbose_name=_("Vendor"))     # Corrected
        def __str__(self):
            return self.name
        class Meta:
            verbose_name = _("Contact")
            verbose_name_plural = _("Contacts")


# --- Helper Functions ---
def is_superuser(user):
    return user.is_superuser

def get_user_safes(user):
    if user.is_superuser:
        return Safe.objects.all()
    return Safe.objects.filter(user_assignments__user=user)

def get_user_total_balance(user):
    safes = get_user_safes(user)
    total_balance = Decimal('0.00')
    for safe_instance in safes:
        income = Transaction.objects.filter(safe=safe_instance, category__type=Category.TRANSACTION_TYPE_INCOME).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        expense = Transaction.objects.filter(safe=safe_instance, category__type=Category.TRANSACTION_TYPE_EXPENSE).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        total_balance += (income - expense)
    return total_balance

# --- Transaction Views ---
@login_required
def transaction_list_view(request):
    user_safes = get_user_safes(request.user)
    
    # Prepare data for each safe
    user_safes_with_transactions = []
    for safe_instance in user_safes:
        transactions_for_safe_asc = Transaction.objects.filter(safe=safe_instance).select_related(
            'category', 'sub_category', 'user', 'contact'
        ).order_by('transaction_date', 'created_at')
        
        current_run_balance = Decimal('0.00')
        annotated_transactions_for_safe = []
        for trans in transactions_for_safe_asc:
            if trans.category.type == Category.TRANSACTION_TYPE_INCOME:
                current_run_balance += trans.amount
            elif trans.category.type == Category.TRANSACTION_TYPE_EXPENSE:
                current_run_balance -= trans.amount
            trans.running_balance = current_run_balance
            annotated_transactions_for_safe.append(trans)
        
        # Sort by date descending for display
        annotated_transactions_for_safe.sort(key=lambda t: t.transaction_date, reverse=True)

        user_safes_with_transactions.append({
            'safe_id': safe_instance.id,
            'safe_name': safe_instance.name,
            'safe_balance': safe_instance.balance, # Added safe's current balance
            'transactions': annotated_transactions_for_safe,
        })

    # Prepare data for combined transactions
    all_transactions_asc = Transaction.objects.filter(safe__in=user_safes).select_related(
        'safe', 'category', 'sub_category', 'user', 'contact'
    ).order_by('transaction_date', 'created_at')

    overall_run_balance = Decimal('0.00')
    combined_transactions_with_balance = []
    for trans in all_transactions_asc:
        if trans.category.type == Category.TRANSACTION_TYPE_INCOME:
            overall_run_balance += trans.amount
        elif trans.category.type == Category.TRANSACTION_TYPE_EXPENSE:
            overall_run_balance -= trans.amount
        trans.running_balance = overall_run_balance
        combined_transactions_with_balance.append(trans)
    
    # Sort by date descending for display
    combined_transactions_with_balance.sort(key=lambda t: t.transaction_date, reverse=True)

    total_balance_display = get_user_total_balance(request.user) # Used for display at the top

    context = {
        'user_safes_with_transactions': user_safes_with_transactions,
        'combined_transactions_with_balance': combined_transactions_with_balance,
        'page_title': _('All Transactions'),
        'total_balance': total_balance_display, # For the summary display
        'user_safes': user_safes, # Still needed for tab generation if not using the more detailed list
        'Category': Category, # Pass Category model for type comparison in template
        'current_date': timezone.now().date(),
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
        'safe', 'category', 'sub_category', 'user', 'contact'
    ).order_by('-transaction_date', '-created_at')
    
    total_balance = get_user_total_balance(request.user)

    today_income = transactions.filter(category__type=Category.TRANSACTION_TYPE_INCOME).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    today_expense = transactions.filter(category__type=Category.TRANSACTION_TYPE_EXPENSE).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    overall_today_net_flow = today_income - today_expense # This is the overall net flow

    safes_data_today = []
    overall_total_balance = get_user_total_balance(request.user) # Renamed from total_balance to avoid conflict

    for safe_instance in user_safes:
        today_transactions_safe = transactions.filter(safe=safe_instance).order_by('-created_at') # Already filtered for today

        today_income_safe = today_transactions_safe.filter(category__type=Category.TRANSACTION_TYPE_INCOME).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        today_expense_safe = today_transactions_safe.filter(category__type=Category.TRANSACTION_TYPE_EXPENSE).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        today_net_flow_safe = today_income_safe - today_expense_safe

        safes_data_today.append({
            'safe_id': safe_instance.id,
            'safe_name': safe_instance.name,
            'safe_balance': safe_instance.balance,
            'transactions': today_transactions_safe,
            'today_net_flow': today_net_flow_safe,
            'today_income': today_income_safe,
            'today_expense': today_expense_safe,
        })

    context = {
        'safes_data_today': safes_data_today, # New structured data for today
        'flat_today_transactions_list': transactions, # For the combined tab, if we want to list all tx
        'page_title': _("Today's Transactions"),
        'total_balance': overall_total_balance, # Sum of all safe balances
        'today_net_flow': overall_today_net_flow, # Changed to match template's top summary variable
        'overall_today_income': today_income, # Overall income for the day for combined tab content
        'overall_today_expense': today_expense, # Overall expense for the day for combined tab content
        'user_safes': user_safes, # For tab generation
        'Category': Category, # For type comparison in template
        'current_date': timezone.now().date(), # For edit/delete lock check
    }
    return render(request, 'cashflow/transaction_list.html', context)

@login_required
def transaction_create_view(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.transaction_date = timezone.now()
            transaction.save()
            return redirect('cashflow:transaction_list')
    else:
        form = TransactionForm(user=request.user)
    
    bill_denominations = [200, 100, 50, 20, 10, 5, 1]
    context = {
        'form': form,
        'page_title': _('New Transaction'),
        'bill_denominations': bill_denominations,
    }
    return render(request, 'cashflow/transaction_form.html', context)

@login_required
def transaction_update_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    user_safes = get_user_safes(request.user)

    if transaction.safe not in user_safes and not request.user.is_superuser:
        return redirect('cashflow:transaction_list')

    if not request.user.is_superuser:
        today = timezone.now().date()
        tx_date = transaction.transaction_date.date()
        if tx_date != today:
            messages.error(request, _("You can only edit or delete transactions from the current day."))
            return redirect('cashflow:transaction_list')

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('cashflow:transaction_list')
    else:
        form = TransactionForm(instance=transaction, user=request.user)

    bill_denominations = [200, 100, 50, 20, 10, 5, 1]
    context = {
        'form': form,
        'transaction': transaction,
        'page_title': _('Edit Transaction'),
        'bill_denominations': bill_denominations,
    }
    return render(request, 'cashflow/transaction_form.html', context)

@login_required
def transaction_delete_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    user_safes = get_user_safes(request.user)

    if transaction.safe not in user_safes and not request.user.is_superuser:
        return redirect('cashflow:transaction_list')

    if not request.user.is_superuser:
        today = timezone.now().date()
        tx_date = transaction.transaction_date.date()
        if tx_date != today:
            messages.error(request, _("You can only edit or delete transactions from the current day."))
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
    transaction_type_code = request.GET.get('transaction_type_code')
    if transaction_type_code in [Category.TRANSACTION_TYPE_INCOME, Category.TRANSACTION_TYPE_EXPENSE]:
        categories = Category.objects.filter(type=transaction_type_code).order_by('name')
        return JsonResponse(list(categories.values('id', 'name')), safe=False)
    return JsonResponse([], safe=False)

@login_required
def ajax_load_subcategories(request):
    category_id = request.GET.get('category_id')
    if category_id:
        try:
            category_id = int(category_id)
            subcategories = SubCategory.objects.filter(category_id=category_id).order_by('name')
            return JsonResponse(list(subcategories.values('id', 'name')), safe=False)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid category_id'}, status=400)
    return JsonResponse([], safe=False)

@login_required
def ajax_load_contacts(request):
    transaction_type_code = request.GET.get('transaction_type_code')
    contacts_qs = Contact.objects.none() 
    contact_label = _("Contact") 

    if transaction_type_code == Category.TRANSACTION_TYPE_INCOME:
        contacts_qs = Contact.objects.filter(customer=True).order_by('name') # Corrected field
        contact_label = _("Customer")
    elif transaction_type_code == Category.TRANSACTION_TYPE_EXPENSE:
        contacts_qs = Contact.objects.filter(vendor=True).order_by('name') # Corrected field
        contact_label = _("Vendor")
            
    contacts_data = list(contacts_qs.values('id', 'name'))
    return JsonResponse({'contacts': contacts_data, 'label': str(contact_label)}, safe=False)


# --- Superuser Configuration Views ---
class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

@login_required
@user_passes_test(is_superuser)
def config_dashboard_view(request):
    context = {'page_title': _('Configuration Dashboard')}
    return render(request, 'cashflow/config_dashboard.html', context)

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

class CategoryListView(SuperuserRequiredMixin, ListView):
    model = Category
    template_name = 'cashflow/config/category_list.html'
    paginate_by = 10 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['income_categories'] = Category.objects.filter(type=Category.TRANSACTION_TYPE_INCOME).order_by('name')
        context['expense_categories'] = Category.objects.filter(type=Category.TRANSACTION_TYPE_EXPENSE).order_by('name')
        context['page_title'] = _('Manage Categories')
        return context

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

class SubCategoryListView(SuperuserRequiredMixin, ListView):
    model = SubCategory
    template_name = 'cashflow/config/subcategory_list.html'
    context_object_name = 'subcategories'
    paginate_by = 10
    def get_queryset(self):
        return SubCategory.objects.all().select_related('category').order_by('category__type', 'category__name', 'name')

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
