# cashflow/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal

# Assuming your contacts app and Contact model are defined as follows:
# from contacts.models import Contact (Ensure this import path is correct for your project)
# For demonstration, let's define a placeholder if contacts.models is not directly accessible here.
try:
    from contacts.models import Contact
except ImportError:
    class Contact(models.Model): # Placeholder
        name = models.CharField(max_length=255)
        CONTACT_TYPE_CHOICES = [
            ('CUSTOMER', _('Customer')),
            ('VENDOR', _('Vendor')),
            ('EMPLOYEE', _('Employee')),
            ('OTHER', _('Other')),
        ]
        contact_type = models.CharField(max_length=10, choices=CONTACT_TYPE_CHOICES, verbose_name=_("Contact Type"))

        def __str__(self):
            return self.name
        class Meta:
            verbose_name = _("Contact")
            verbose_name_plural = _("Contacts")


class Safe(models.Model):
    """
    Represents a cash safe or bank account.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Safe Name"))
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), verbose_name=_("Current Balance"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Safe")
        verbose_name_plural = _("Safes")
        ordering = ['name']

    def __str__(self):
        return self.name

    def update_balance(self):
        """
        Recalculates the balance based on all transactions.
        This can be resource-intensive. Signals are a better approach for live updates.
        """
        total_income = self.transactions.filter(
            category__transaction_type__name__in=[_('Income'), _('Internal Transfer In')]
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        total_expense = self.transactions.filter(
            category__transaction_type__name__in=[_('Expense'), _('Internal Transfer Out')]
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        self.balance = total_income - total_expense
        self.save(update_fields=['balance'])


class TransactionType(models.Model):
    """
    Defines the type of transaction (e.g., Income, Expense, Internal Transfer).
    """
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Transaction Type Name"))

    class Meta:
        verbose_name = _("Transaction Type")
        verbose_name_plural = _("Transaction Types")
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Categories for transactions, linked to a TransactionType.
    """
    name = models.CharField(max_length=100, verbose_name=_("Category Name"))
    transaction_type = models.ForeignKey(TransactionType, on_delete=models.CASCADE, related_name='categories', verbose_name=_("Transaction Type"))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        unique_together = ('name', 'transaction_type')
        ordering = ['transaction_type', 'name']

    def __str__(self):
        return f"{self.transaction_type.name} - {self.name}"


class SubCategory(models.Model):
    """
    Subcategories for transactions, linked to a Category.
    """
    name = models.CharField(max_length=100, verbose_name=_("SubCategory Name"))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories', verbose_name=_("Category"))

    class Meta:
        verbose_name = _("SubCategory")
        verbose_name_plural = _("SubCategories")
        unique_together = ('name', 'category')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.category} - {self.name}"


class Transaction(models.Model):
    """
    Represents a single financial transaction.
    """
    PAYMENT_METHOD_CASH = 'cash'
    PAYMENT_METHOD_CHECK = 'check'
    PAYMENT_METHOD_BANK_TRANSFER = 'bank_transfer'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_CASH, _('Cash')),
        (PAYMENT_METHOD_CHECK, _('Check')),
        (PAYMENT_METHOD_BANK_TRANSFER, _('Bank Transfer')),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_("User"), help_text=_("The user who recorded this transaction."))
    safe = models.ForeignKey(Safe, on_delete=models.PROTECT, related_name='transactions', verbose_name=_("Safe"))
    # transaction_type is implicitly defined by Category's transaction_type.
    # We keep category directly.
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions', verbose_name=_("Category"))
    sub_category = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_("SubCategory"))
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Sender/Receiver Name"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("Amount"))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name=_("Payment Method"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    transaction_date = models.DateTimeField(default=timezone.now, verbose_name=_("Transaction Date"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.category} - {self.amount} ({self.safe.name})"

    @property
    def get_transaction_type_name(self):
        """Helper to get the transaction type name from the category."""
        return self.category.transaction_type.name


class UserSafeAssignment(models.Model):
    """
    Assigns users to safes they can access.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='safe_assignments', verbose_name=_("User"))
    safe = models.ForeignKey(Safe, on_delete=models.CASCADE, related_name='user_assignments', verbose_name=_("Safe"))
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Assigned At"))

    class Meta:
        verbose_name = _("User Safe Assignment")
        verbose_name_plural = _("User Safe Assignments")
        unique_together = ('user', 'safe') # A user can be assigned to a safe only once
        ordering = ['user', 'safe']

    def __str__(self):
        return f"{self.user.username} - {self.safe.name}"


# Signals to update Safe balance
@receiver(post_save, sender=Transaction)
def update_safe_balance_on_save(sender, instance, created, **kwargs):
    """
    Updates the safe balance when a transaction is saved.
    """
    safe = instance.safe
    transaction_type_name = instance.category.transaction_type.name

    # Use a more robust way to identify income/expense types if names change due to translation
    # For now, relying on the translated names provided in the prompt.
    # Consider adding a boolean field 'is_income_type' to TransactionType model for robustness.
    
    # This logic assumes transaction_type names are consistent.
    # It's better to have a 'type_effect' field in TransactionType (e.g., +1 for income, -1 for expense)
    
    # Recalculate the entire balance for accuracy, though it's less performant.
    # A more performant way would be to adjust based on the change,
    # but recalculation ensures consistency if other updates happen.
    safe.update_balance()


@receiver(post_delete, sender=Transaction)
def update_safe_balance_on_delete(sender, instance, **kwargs):
    """
    Updates the safe balance when a transaction is deleted.
    """
    safe = instance.safe
    # Similar to on_save, recalculate for accuracy.
    safe.update_balance()

