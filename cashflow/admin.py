# cashflow/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Safe, Category, SubCategory, Transaction, UserSafeAssignment # Removed TransactionType

@admin.register(Safe)
class SafeAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance', 'created_at', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('balance', 'created_at', 'updated_at') 

# TransactionTypeAdmin is removed

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type') # Changed from transaction_type
    search_fields = ('name',)
    list_filter = ('type',) # Changed from transaction_type

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'get_category_type')
    search_fields = ('name', 'category__name', 'category__type')
    list_filter = ('category__type', 'category',)

    @admin.display(description=_('Category Type'), ordering='category__type')
    def get_category_type(self, obj):
        return obj.category.get_type_display()


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'safe', 'get_category_type_display' ,'category', 'sub_category', 'amount', 'payment_method', 'user', 'contact')
    search_fields = ('safe__name', 'category__name', 'sub_category__name', 'notes', 'contact__name', 'user__username')
    list_filter = ('transaction_date', 'safe', 'category__type', 'category', 'payment_method', 'user')
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
            'classes': ('collapse',) 
        }),
    )

    @admin.display(description=_('Transaction Type'), ordering='category__type')
    def get_category_type_display(self, obj):
        return obj.category.get_type_display()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'safe', 'category', 'sub_category', 'user', 'contact'
        )


@admin.register(UserSafeAssignment)
class UserSafeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'safe', 'assigned_at')
    search_fields = ('user__username', 'safe__name')
    list_filter = ('safe',)
    autocomplete_fields = ['user', 'safe']
