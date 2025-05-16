from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Q
from .models import SparePartRequest, Category
from .forms import (
    SparePartRequestForm, CategoryForm, SupervisorConfirmOrderForm,
    UserConfirmReceptionForm, SupervisorSparePartEditForm
)
from django.core.paginator import Paginator # For category management if not using DataTables there
from django.utils.translation import gettext_lazy as _
import json

# --- Helper Functions ---
def is_supervisor(user):
    """
    Checks if a user is a supervisor.
    Implement your own logic, e.g., checking group membership or a UserProfile field.
    For now, superusers are considered supervisors.
    """
    if not user or not user.is_authenticated:
        return False
    # Example: return user.groups.filter(name='Supervisors').exists() or user.is_superuser
    # Example: return hasattr(user, 'userprofile') and user.userprofile.sector_number == 1
    return user.is_superuser # Placeholder

def is_melsheraiy(user):
    """Checks if the user is 'melsheraiy' for category management."""
    return user.is_authenticated and user.username == 'melsheraiy'

def get_user_sector_info(user):
    """
    Placeholder to get sector info. Implement based on your UserProfile or other system.
    Returns a dict {'sector_name': '...', 'sector_number': ...}
    """
    if hasattr(user, 'userprofile'): # Assuming you have a UserProfile model linked to User
        return {'sector_name': user.userprofile.sector_name, 'sector_number': user.userprofile.sector_number}
    # Fallback or default if no profile/sector info
    return {'sector_name': _('Default Sector'), 'sector_number': 0}


# --- Main App View ---
@login_required
def spare_parts_index(request):
    user_info = get_user_sector_info(request.user)
    context = {
        'username': request.user.username,
        'sector_name': user_info.get('sector_name', _('N/A')),
        'sector_number': user_info.get('sector_number', 0),
        'is_melsheraiy': is_melsheraiy(request.user),
        'is_supervisor': is_supervisor(request.user),
        'form': SparePartRequestForm(), # For the "New Entry" section
        # Supervisor form if applicable, determined by JS or separate rendering logic
        'supervisor_form': SupervisorSparePartEditForm() if is_supervisor(request.user) else None,
    }
    return render(request, 'spare_parts/spare_parts_index.html', context)

# --- Category Management Views (for 'melsheraiy' or Supervisors) ---
@login_required
@user_passes_test(lambda u: is_melsheraiy(u) or is_supervisor(u))
def manage_categories(request):
    """Page for managing categories. Data will be loaded/managed via AJAX."""
    form = CategoryForm()
    return render(request, 'spare_parts/manage_categories.html', {'form': form})

@require_GET
@login_required
@user_passes_test(lambda u: is_melsheraiy(u) or is_supervisor(u))
def list_categories_api(request):
    """API endpoint to list all categories for dropdowns or management table."""
    categories = Category.objects.all().order_by('name')
    # For DataTables on manage_categories page
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('datatables'):
        data = [[cat.id, cat.name] for cat in categories]
        return JsonResponse({'data': data})
    # For general dropdown population
    data = list(categories.values('id', 'name'))
    return JsonResponse(data, safe=False)


@require_POST
@login_required
@user_passes_test(lambda u: is_melsheraiy(u) or is_supervisor(u))
def add_category_api(request):
    form = CategoryForm(request.POST)
    if form.is_valid():
        category = form.save()
        return JsonResponse({'success': True, 'id': category.id, 'name': category.name})
    return JsonResponse({'success': False, 'errors': form.errors.get_json_data()}, status=400)

@require_POST # Or PUT
@login_required
@user_passes_test(lambda u: is_melsheraiy(u) or is_supervisor(u))
def edit_category_api(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST, instance=category)
    if form.is_valid():
        category = form.save()
        return JsonResponse({'success': True, 'id': category.id, 'name': category.name})
    return JsonResponse({'success': False, 'errors': form.errors.get_json_data()}, status=400)

@require_POST # Or DELETE
@login_required
@user_passes_test(lambda u: is_melsheraiy(u) or is_supervisor(u))
def delete_category_api(request, pk):
    category = get_object_or_404(Category, pk=pk)
    try:
        category.delete()
        return JsonResponse({'success': True})
    except models.ProtectedError:
        return JsonResponse({'success': False, 'error': _('Cannot delete category as it is used in existing requests.')}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# --- DataTables Data Source Views ---
def _format_entry_for_datatables(entry, current_user):
    photo_data = {'url': entry.photo.url if entry.photo else "", 'thumbnail': entry.photo.url if entry.photo else ""} # Basic thumbnail, consider sorl-thumbnail
    user_sector_info = get_user_sector_info(current_user)

    return [
        entry.id,
        entry.sector_name or _("N/A"),
        entry.category.name,
        entry.description,
        str(entry.requested_qty),
        entry.get_unit_display(),
        entry.notes or "",
        photo_data,
        str(entry.ordered_qty) if entry.ordered_qty is not None else "",
        str(entry.received_qty) if entry.received_qty is not None else "",
        entry.get_status_display(),
        entry.created_at.strftime("%Y-%m-%d"),
        entry.created_at.strftime("%H:%M"), # Apps Script showed HH:mm
        entry.user.username,
        # Additional data for actions rendering if needed (passed implicitly via row data to JS)
    ]

def _get_filtered_entries(request, status_list=None, date_filter_type=None):
    queryset = SparePartRequest.objects.select_related('user', 'category', 'last_updated_by').all()
    user_sector_info = get_user_sector_info(request.user)

    # Filter by user's sector if not a supervisor
    # if not is_supervisor(request.user):
    #     queryset = queryset.filter(sector_number=user_sector_info.get('sector_number'))
    # Or, more simply, if users should only see their own requests unless they are supervisors:
    if not is_supervisor(request.user):
         queryset = queryset.filter(user=request.user)


    if status_list:
        queryset = queryset.filter(status__in=status_list)

    if date_filter_type:
        today_date = timezone.now().date()
        if date_filter_type == "today":
            queryset = queryset.filter(created_at__date=today_date)
        elif date_filter_type == "month":
            queryset = queryset.filter(created_at__year=today_date.year, created_at__month=today_date.month)

    data = [_format_entry_for_datatables(entry, request.user) for entry in queryset]
    return JsonResponse({'data': data})

@login_required
def get_new_requests_data(request):
    return _get_filtered_entries(request, status_list=[SparePartRequest.STATUS_NEW])

@login_required
def get_ordered_waiting_data(request):
    return _get_filtered_entries(request, status_list=[SparePartRequest.STATUS_ORDERED])

@login_required
def get_received_data(request):
    return _get_filtered_entries(request, status_list=[SparePartRequest.STATUS_RECEIVED])

@login_required
def get_today_entries_data(request):
    return _get_filtered_entries(request, date_filter_type="today")

@login_required
def get_month_entries_data(request):
    return _get_filtered_entries(request, date_filter_type="month")


# --- Entry Action API Views ---
@require_GET
@login_required
def get_entry_details_api(request, entry_id):
    try:
        # Ensure user can only access their own requests or if supervisor
        entry_q = SparePartRequest.objects.select_related('category')
        if not is_supervisor(request.user):
            entry_q = entry_q.filter(Q(user=request.user) | Q(sector_number=get_user_sector_info(request.user).get('sector_number'))) # Example permission
        entry = entry_q.get(pk=entry_id)
    except SparePartRequest.DoesNotExist:
        return JsonResponse({'error': _('Request not found or access denied.')}, status=404)

    data = {
        'id': entry.id,
        'category_id': entry.category_id,
        'description': entry.description,
        'requested_qty': str(entry.requested_qty),
        'unit': entry.unit,
        'notes': entry.notes or "",
        'photo_url': entry.photo.url if entry.photo else '',
        'status': entry.status, # Current status for the form
        'ordered_qty': str(entry.ordered_qty) if entry.ordered_qty is not None else "", # For modals
        'received_qty': str(entry.received_qty) if entry.received_qty is not None else "", # For modals
    }
    return JsonResponse(data)

@require_POST
@login_required
def save_spare_part_entry_api(request):
    entry_id = request.POST.get('id')
    instance = None
    user_sector_info = get_user_sector_info(request.user)

    if entry_id:
        try:
            # Permission check: user can edit their own, or supervisor can edit any from their sector/all
            q_filter = Q(pk=entry_id)
            if not is_supervisor(request.user):
                q_filter &= Q(user=request.user) # Can only edit their own
            instance = SparePartRequest.objects.get(q_filter)
        except SparePartRequest.DoesNotExist:
             return JsonResponse({'success': False, 'message': _('Request not found or permission denied to edit.')}, status=404)

    # Supervisors use a different form that allows status changes
    if instance and is_supervisor(request.user) and instance.status != SparePartRequest.STATUS_NEW: # Allow supervisor to edit more fields
        form = SupervisorSparePartEditForm(request.POST, request.FILES, instance=instance)
    else: # New entry or user editing their own 'New' request
        form = SparePartRequestForm(request.POST, request.FILES, instance=instance)

    if form.is_valid():
        entry = form.save(commit=False)
        if not instance: # New entry
            entry.user = request.user
            entry.sector_name = user_sector_info.get('sector_name')
            entry.sector_number = user_sector_info.get('sector_number')
            entry.status = SparePartRequest.STATUS_NEW # Default for new
        entry.last_updated_by = request.user

        # Handle photo removal if 'remove_photo' checkbox is checked
        if form.cleaned_data.get('remove_photo') and instance and instance.photo:
            instance.photo.delete(save=False) # Delete file from storage
            entry.photo = None # Clear the field

        # Specific logic for SupervisorSparePartEditForm
        if isinstance(form, SupervisorSparePartEditForm):
            entry.status = form.cleaned_data['status']
            if entry.status == SparePartRequest.STATUS_RECEIVED:
                entry.received_qty = form.cleaned_data['received_qty_form_input']
            # If status changed from Received to something else, nullify received_qty? (Business rule)
            # elif instance and instance.status == SparePartRequest.STATUS_RECEIVED and entry.status != SparePartRequest.STATUS_RECEIVED:
            #     entry.received_qty = None

        entry.save()
        # form.save_m2m() # If you have ManyToManyFields

        return JsonResponse({'success': True, 'message': _('Request saved successfully.'), 'entryId': entry.id})
    else:
        return JsonResponse({'success': False, 'message': _('Please correct the errors below.'), 'errors': form.errors.get_json_data()}, status=400)


@require_POST # Or use DELETE method
@login_required
def delete_spare_part_entry_api(request, entry_id):
    try:
        # Permission: User can delete their own 'New' requests, or supervisor can delete.
        q_filter = Q(pk=entry_id)
        if not is_supervisor(request.user):
            q_filter &= Q(user=request.user, status=SparePartRequest.STATUS_NEW)

        entry = SparePartRequest.objects.get(q_filter)
    except SparePartRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': _('Request not found or permission denied to delete.')}, status=404)

    # Log deletion if needed
    entry_description_for_log = entry.description[:50]
    entry.delete()
    return JsonResponse({'success': True, 'message': _(f'Request "{entry_description_for_log}..." deleted successfully.')})


@require_POST
@login_required
@user_passes_test(is_supervisor) # Only supervisors can confirm orders
def confirm_order_placed_api(request, entry_id):
    entry = get_object_or_404(SparePartRequest, pk=entry_id, status=SparePartRequest.STATUS_NEW) # Can only confirm 'New'
    form = SupervisorConfirmOrderForm(request.POST)
    if form.is_valid():
        entry.ordered_qty = form.cleaned_data['ordered_qty']
        entry.status = SparePartRequest.STATUS_ORDERED
        entry.last_updated_by = request.user
        entry.save()
        return JsonResponse({'success': True, 'message': _('Order confirmed successfully.')})
    return JsonResponse({'success': False, 'errors': form.errors.get_json_data()}, status=400)

@require_POST
@login_required
def confirm_item_reception_api(request, entry_id):
    try:
        # User can confirm reception for their sector's 'Ordered' requests, or supervisor can.
        q_filter = Q(pk=entry_id, status=SparePartRequest.STATUS_ORDERED)
        # if not is_supervisor(request.user):
        #    user_sector_info = get_user_sector_info(request.user)
        #    q_filter &= Q(sector_number=user_sector_info.get('sector_number'))
        # Simpler: only user who requested or supervisor
        q_filter_user_specific = Q(user=request.user)
        if is_supervisor(request.user): # Supervisor can confirm any ordered item
             entry = SparePartRequest.objects.get(q_filter)
        else: # Regular user can only confirm their own
            entry = SparePartRequest.objects.get(q_filter & q_filter_user_specific)

    except SparePartRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': _('Request not found, not in correct status, or permission denied.')}, status=404)

    form = UserConfirmReceptionForm(request.POST)
    if form.is_valid():
        entry.received_qty = form.cleaned_data['received_qty']
        entry.status = SparePartRequest.STATUS_RECEIVED
        entry.last_updated_by = request.user
        entry.save()
        return JsonResponse({'success': True, 'message': _('Item reception confirmed successfully.')})
    return JsonResponse({'success': False, 'errors': form.errors.get_json_data()}, status=400)

