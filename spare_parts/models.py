from django.db import models
from django.conf import settings # To get the User model
from django.utils.translation import gettext_lazy as _ # For verbose names

# You might have a UserProfile model like this in your accounts app or main app
# For now, we'll assume sector_name and sector_number are derived or handled in views/forms.
# class UserProfile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     sector_name = models.CharField(max_length=100, blank=True, null=True)
#     sector_number = models.IntegerField(blank=True, null=True) # 1 for Supervisor, etc.
#
#     def __str__(self):
#         return self.user.username

class Category(models.Model):
    name = models.CharField(_("Category Name"), max_length=100, unique=True)
    # If categories were sector-specific (they are not, melsheraiy manages them globally):
    # sector_number = models.IntegerField(blank=True, null=True, help_text="Leave blank if global, or specify sector number.")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']

class SparePartRequest(models.Model):
    STATUS_NEW = 'New'
    STATUS_ORDERED = 'Ordered' # Short for "Ordered and Waiting for Delivery"
    STATUS_RECEIVED = 'Received'

    STATUS_CHOICES = [
        (STATUS_NEW, _('New Request')),
        (STATUS_ORDERED, _('Ordered and Waiting for Delivery')),
        (STATUS_RECEIVED, _('Received')),
    ]
    UNIT_CHOICES = [
        ('قطعة', _('Piece')),
        ('طقم', _('Set')),
        ('كرتونة', _('Carton')),
        ('كيلو جرام', _('Kilogram')),
        ('متر', _('Meter')),
        ('لتر', _('Liter')),
        ('علبة', _('Can/Box')),
        ('دستة', _('Dozen')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT, # Prevent deleting user if they have requests; consider SET_NULL
        verbose_name=_("Requester")
    )
    # These fields are from the original Apps Script logic where user data included sector info.
    # In Django, this might come from a UserProfile or be dynamically determined.
    # For simplicity, we'll make them optional or populate them in the view if needed.
    sector_name = models.CharField(_("Sector Name"), max_length=100, blank=True, null=True)
    sector_number = models.IntegerField(_("Sector Number"), blank=True, null=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT, # Prevent deleting category if used in requests
        verbose_name=_("Category")
    )
    description = models.TextField(_("Description"))
    requested_qty = models.DecimalField(_("Requested Quantity"), max_digits=10, decimal_places=2)
    unit = models.CharField(_("Unit"), max_length=50, choices=UNIT_CHOICES)
    notes = models.TextField(_("Notes"), blank=True, null=True)
    photo = models.ImageField(_("Photo"), upload_to='spare_parts_photos/', blank=True, null=True)

    ordered_qty = models.DecimalField(_("Ordered Quantity"), max_digits=10, decimal_places=2, blank=True, null=True)
    received_qty = models.DecimalField(_("Received Quantity"), max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Last Updated At"), auto_now=True)
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='updated_spare_part_requests',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Last Updated By")
    )

    def __str__(self):
        return f"Request ID {self.id} - {self.description[:50]} by {self.user.username}"

    class Meta:
        verbose_name = _("Spare Part Request")
        verbose_name_plural = _("Spare Part Requests")
        ordering = ['-created_at'] # Default ordering, newest first

# Optional: Log model for edits/deletions if needed
# class SparePartRequestLog(models.Model):
#     ACTION_CHOICES = [('EDIT', 'Edit'), ('DELETE', 'Delete'), ('STATUS_CHANGE', 'Status Change')]
#     request_instance = models.ForeignKey(SparePartRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
#     original_request_id = models.IntegerField(null=True, blank=True) # In case the request itself is deleted
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
#     action = models.CharField(max_length=20, choices=ACTION_CHOICES)
#     timestamp = models.DateTimeField(auto_now_add=True)
#     details = models.JSONField(null=True, blank=True) # Store old values or specific changes

#     def __str__(self):
#         return f"{self.action} on Request {self.original_request_id or self.request_instance_id} by {self.user} at {self.timestamp}"

