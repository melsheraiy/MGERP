# cashflow/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal

# Attempt to import the actual Contact model from the contacts app
try:
    from contacts.models import Contact as ActualContact
    Contact = ActualContact 
except ImportError:
    class Contact(models.Model): 
        name = models.CharField(max_length=255, verbose_name=_("Name"))
        customer = models.BooleanField(default=False, verbose_name=_("Customer"))
        vendor = models.BooleanField(default=False, verbose_name=_("Vendor"))

        def __str__(self):
            return self.name
        class Meta:
            verbose_name = _("Contact Placeholder")
            verbose_name_plural = _("Contact Placeholders")
            # To prevent this placeholder from creating its own migrations if 'contacts' app is missing:
            # managed = False 


class Safe(models.Model):
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
        total_income_amount = Decimal('0.00')
        total_expense_amount = Decimal('0.00')
        for transaction in self.transactions.all().select_related('category'):
            if transaction.category.type == Category.TRANSACTION_TYPE_INCOME:
                total_income_amount += transaction.amount
            elif transaction.category.type == Category.TRANSACTION_TYPE_EXPENSE:
                total_expense_amount += transaction.amount
        self.balance = total_income_amount - total_expense_amount
        self.save(update_fields=['balance'])


class Category(models.Model):
    TRANSACTION_TYPE_INCOME = 'INCOME'
    TRANSACTION_TYPE_EXPENSE = 'EXPENSE'
    TYPE_CHOICES = [
        (TRANSACTION_TYPE_INCOME, _('Income')),
        (TRANSACTION_TYPE_EXPENSE, _('Expense')),
    ]

    name = models.CharField(max_length=100, verbose_name=_("Category Name"))
    # Made type nullable for the initial migration and removed default for now
    type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES, 
        verbose_name=_("Transaction Type"),
        null=True, # Allow null temporarily
        blank=True # Allow blank in forms temporarily if needed, though primarily for DB
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        # Temporarily remove unique_together to allow data cleanup
        # unique_together = ('name', 'type') 
        ordering = ['type', 'name']

    def __str__(self):
        return f"{self.get_type_display() if self.type else _('Uncategorized')} - {self.name}"


class SubCategory(models.Model):
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
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions', verbose_name=_("Category"))
    sub_category = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_("SubCategory"))
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Contact")) 
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
    def get_transaction_type_display(self):
        return self.category.get_type_display()
    
    @property
    def get_transaction_type_code(self):
        return self.category.type


class UserSafeAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='safe_assignments', verbose_name=_("User"))
    safe = models.ForeignKey(Safe, on_delete=models.CASCADE, related_name='user_assignments', verbose_name=_("Safe"))
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Assigned At"))
    is_default = models.BooleanField(default=False, verbose_name=_("Default Safe"))

    def save(self, *args, **kwargs):
        if self.is_default:
            # Unset other default assignments for this user
            UserSafeAssignment.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("User Safe Assignment")
        verbose_name_plural = _("User Safe Assignments")
        unique_together = ('user', 'safe') 
        ordering = ['user', 'safe']

    def __str__(self):
        return f"{self.user.username} - {self.safe.name}"

@receiver(post_save, sender=Transaction)
def update_safe_balance_on_save(sender, instance, created, **kwargs):
    instance.safe.update_balance()

@receiver(post_delete, sender=Transaction)
def update_safe_balance_on_delete(sender, instance, **kwargs):
    instance.safe.update_balance()
