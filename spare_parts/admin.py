from django.contrib import admin
from .models import Category, SparePartRequest

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(SparePartRequest)
class SparePartRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'category', 'description_short', 'requested_qty', 'unit',
        'status', 'created_at', 'last_updated_by'
    )
    list_filter = ('status', 'category', 'user', 'created_at', 'sector_name')
    search_fields = ('id', 'description', 'user__username', 'category__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    fieldsets = (
        (None, {
            'fields': ('user', ('sector_name', 'sector_number'), 'category', 'description', 'notes')
        }),
        ('Quantity & Unit', {
            'fields': (('requested_qty', 'unit'),)
        }),
        ('Photo', {
            'fields': ('photo',)
        }),
        ('Status & Processing (Managed by System/Supervisor)', {
            'fields': ('status', 'ordered_qty', 'received_qty', 'last_updated_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',) # Collapsible section
        }),
    )

    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'

    def save_model(self, request, obj, form, change):
        if not change: # If creating a new object
            obj.user = request.user # Default user to current admin user if not set
        obj.last_updated_by = request.user
        super().save_model(request, obj, form, change)

# If you implement UserProfile, register it too.
# from .models import UserProfile
# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
# list_display = ('user', 'sector_name', 'sector_number')
# search_fields = ('user__username', 'sector_name')
