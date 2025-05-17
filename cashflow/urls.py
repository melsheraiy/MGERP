# cashflow/urls.py
from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'cashflow'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='cashflow:transaction_list', permanent=False), name='index'), 
    
    path('transactions/', views.transaction_list_view, name='transaction_list'),
    path('transactions/today/', views.today_transactions_view, name='today_transactions'),
    path('transactions/new/', views.transaction_create_view, name='transaction_create'),
    path('transactions/<int:pk>/edit/', views.transaction_update_view, name='transaction_update'),
    path('transactions/<int:pk>/delete/', views.transaction_delete_view, name='transaction_delete'),

    # AJAX URLs for dynamic form filtering
    path('ajax/load-categories/', views.ajax_load_categories, name='ajax_load_categories'), # Now takes type (INCOME/EXPENSE)
    path('ajax/load-subcategories/', views.ajax_load_subcategories, name='ajax_load_subcategories'),
    path('ajax/load-contacts/', views.ajax_load_contacts, name='ajax_load_contacts'), 

    path('config/', views.config_dashboard_view, name='config_dashboard'),
    
    path('config/safes/', views.SafeListView.as_view(), name='safe_list'),
    path('config/safes/new/', views.SafeCreateView.as_view(), name='safe_create'),
    path('config/safes/<int:pk>/edit/', views.SafeUpdateView.as_view(), name='safe_update'),
    path('config/safes/<int:pk>/delete/', views.SafeDeleteView.as_view(), name='safe_delete'),

    # TransactionType URLs are removed
    
    path('config/categories/', views.CategoryListView.as_view(), name='category_list'),
    path('config/categories/new/', views.CategoryCreateView.as_view(), name='category_create'),
    path('config/categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('config/categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    path('config/subcategories/', views.SubCategoryListView.as_view(), name='subcategory_list'),
    path('config/subcategories/new/', views.SubCategoryCreateView.as_view(), name='subcategory_create'),
    path('config/subcategories/<int:pk>/edit/', views.SubCategoryUpdateView.as_view(), name='subcategory_update'),
    path('config/subcategories/<int:pk>/delete/', views.SubCategoryDeleteView.as_view(), name='subcategory_delete'),

    path('config/assign-safes/', views.UserSafeAssignmentListView.as_view(), name='usersafeassignment_list'),
    path('config/assign-safes/new/', views.UserSafeAssignmentCreateView.as_view(), name='usersafeassignment_create'),
    path('config/assign-safes/<int:pk>/delete/', views.UserSafeAssignmentDeleteView.as_view(), name='usersafeassignment_delete'),
]
