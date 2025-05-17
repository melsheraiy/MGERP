# cashflow/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Safe, TransactionType, Category, SubCategory, Transaction, UserSafeAssignment

@admin.register(Safe)
class SafeAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance', 'created_at', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('balance', 'created_at', 'updated_at') # Balance is calculated

@admin.register(TransactionType)
class TransactionTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'transaction_type')
    search_fields = ('name', 'transaction_type__name')
    list_filter = ('transaction_type',)

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name', 'category__name', 'category__transaction_type__name')
    list_filter = ('category__transaction_type', 'category',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'safe', 'category', 'sub_category', 'amount', 'payment_method', 'user', 'contact')
    search_fields = ('safe__name', 'category__name', 'sub_category__name', 'notes', 'contact__name', 'user__username')
    list_filter = ('transaction_date', 'safe', 'category__transaction_type', 'category', 'payment_method', 'user')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('transaction_date', 'safe', 'category', 'sub_category', 'amount')
        }),
        (_('Details'), {
            'fields': ('payment_method', 'contact', 'notes', 'user')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',) # Collapsible section
        }),
    )

    def get_queryset(self, request):
        # Optimize query by prefetching related objects
        return super().get_queryset(request).select_related('safe', 'category', 'category__transaction_type', 'sub_category', 'user', 'contact')


@admin.register(UserSafeAssignment)
class UserSafeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'safe', 'assigned_at')
    search_fields = ('user__username', 'safe__name')
    list_filter = ('safe',)
    autocomplete_fields = ['user', 'safe'] # Makes selection easier for large numbers of users/safes

