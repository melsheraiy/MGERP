from django.urls import path
from . import views

app_name = 'spare_parts'

urlpatterns = [
    # Main index page for the spare parts app
    path('', views.spare_parts_index, name='index'),

    # Category Management (for 'melsheraiy' or supervisors)
    path('categories/manage/', views.manage_categories, name='manage_categories'),
    # These category actions are now AJAX-based from the manage_categories page
    path('api/categories/add/', views.add_category_api, name='api_add_category'),
    path('api/categories/<int:pk>/edit/', views.edit_category_api, name='api_edit_category'),
    path('api/categories/<int:pk>/delete/', views.delete_category_api, name='api_delete_category'),
    path('api/categories/list/', views.list_categories_api, name='api_list_categories'), # For populating dropdowns dynamically

    # DataTables AJAX data sources
    path('api/data/new-requests/', views.get_new_requests_data, name='data_new_requests'),
    path('api/data/ordered-waiting/', views.get_ordered_waiting_data, name='data_ordered_waiting'),
    path('api/data/received/', views.get_received_data, name='data_received'),
    path('api/data/today-entries/', views.get_today_entries_data, name='data_today_entries'),
    path('api/data/month-entries/', views.get_month_entries_data, name='data_month_entries'),

    # Entry actions (forms, details for AJAX)
    path('api/entry/save/', views.save_spare_part_entry_api, name='api_save_entry'), # Handles both new and edit via POST
    path('api/entry/<int:entry_id>/details/', views.get_entry_details_api, name='api_get_entry_details'), # GET
    path('api/entry/<int:entry_id>/delete/', views.delete_spare_part_entry_api, name='api_delete_entry'), # POST or DELETE

    # Supervisor/User actions (modals)
    path('api/entry/<int:entry_id>/confirm-order/', views.confirm_order_placed_api, name='api_confirm_order'), # POST
    path('api/entry/<int:entry_id>/confirm-reception/', views.confirm_item_reception_api, name='api_confirm_reception'), # POST
]
