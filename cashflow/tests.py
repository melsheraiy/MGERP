from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
from .models import Safe, Category, Transaction, UserSafeAssignment

# --- Helper Functions ---
def create_user(username='testuser', is_superuser=False):
    return User.objects.create_user(username=username, password='password', is_superuser=is_superuser)

def create_category(name, type):
    return Category.objects.create(name=name, type=type)

def create_safe(name='Test Safe'):
    return Safe.objects.create(name=name)

class TransactionFormTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.safe = create_safe()
        # Assign safe to user (assuming non-superuser needs assignment)
        UserSafeAssignment.objects.create(user=self.user, safe=self.safe)
        self.income_category = create_category('Salary', Category.TRANSACTION_TYPE_INCOME)

    def test_transaction_date_not_in_form(self):
        from .forms import TransactionForm
        form = TransactionForm(user=self.user)
        self.assertNotIn('transaction_date', form.fields)

    def test_transaction_create_view_sets_date_and_user(self):
        transaction_data = {
            'safe': self.safe.pk,
            'transaction_type_selector': Category.TRANSACTION_TYPE_INCOME, # From the form
            'category': self.income_category.pk,
            'amount': Decimal('1000.00'),
            'payment_method': Transaction.PAYMENT_METHOD_BANK,
            # 'notes': 'Test income', # Optional
        }
        
        response = self.client.post(reverse('cashflow:transaction_create'), data=transaction_data)
        
        self.assertEqual(response.status_code, 302, "Should redirect after successful creation") # Redirects to list view
        self.assertTrue(Transaction.objects.exists(), "Transaction should be created")
        
        transaction = Transaction.objects.first()
        self.assertEqual(transaction.safe, self.safe)
        self.assertEqual(transaction.category, self.income_category)
        self.assertEqual(transaction.amount, Decimal('1000.00'))
        
        # Verify transaction_date is set to timezone.now() (approximately)
        self.assertIsNotNone(transaction.transaction_date)
        self.assertEqual(transaction.transaction_date.date(), timezone.now().date())
        # Check if the time is recent (e.g., within the last 5 seconds)
        time_difference = timezone.now() - transaction.transaction_date
        self.assertTrue(time_difference.total_seconds() < 5, "Transaction time should be very recent")
        
        # Verify transaction.user is set to the logged-in user
        self.assertEqual(transaction.user, self.user)

class TransactionListViewTests(TestCase):
    def setUp(self):
        self.user = create_user(username='listviewuser')
        self.client = Client()
        self.client.login(username='listviewuser', password='password')
        
        self.safe1 = create_safe(name='Safe Alpha')
        UserSafeAssignment.objects.create(user=self.user, safe=self.safe1)

        self.income_cat = create_category('Consulting Income', Category.TRANSACTION_TYPE_INCOME)
        self.expense_cat = create_category('Office Supplies', Category.TRANSACTION_TYPE_EXPENSE)

        # Create transactions with specific dates and amounts for predictable ordering and balance
        # Transactions are created in chronological order for easier balance calculation logic
        # They will be sorted by date descending in the view for display
        self.t1_income = Transaction.objects.create(
            user=self.user, safe=self.safe1, category=self.income_cat, 
            amount=Decimal('500.00'), transaction_date=timezone.now() - timezone.timedelta(days=2)
        )
        self.t2_expense = Transaction.objects.create(
            user=self.user, safe=self.safe1, category=self.expense_cat,
            amount=Decimal('50.00'), transaction_date=timezone.now() - timezone.timedelta(days=1)
        )
        self.t3_income = Transaction.objects.create(
            user=self.user, safe=self.safe1, category=self.income_cat,
            amount=Decimal('200.00'), transaction_date=timezone.now() 
        )
        # Expected running balances (chronological):
        # t1: 500.00
        # t2: 500.00 - 50.00 = 450.00
        # t3: 450.00 + 200.00 = 650.00

    def test_running_balance_single_safe_and_data_integrity(self):
        response = self.client.get(reverse('cashflow:transaction_list'))
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertIn('user_safes_with_transactions', context)
        
        user_safes_data = context['user_safes_with_transactions']
        self.assertEqual(len(user_safes_data), 1) # Only one safe assigned/created for this user

        safe1_data = user_safes_data[0]
        self.assertEqual(safe1_data['safe_name'], self.safe1.name)
        
        # Transactions are displayed in reverse chronological order
        displayed_transactions = safe1_data['transactions'] 
        self.assertEqual(len(displayed_transactions), 3)

        # Check transactions and their running balances (order is reversed from creation)
        # Transaction t3 (latest)
        self.assertEqual(displayed_transactions[0].pk, self.t3_income.pk)
        self.assertEqual(displayed_transactions[0].running_balance, Decimal('650.00'))
        self.assertEqual(displayed_transactions[0].category.type, Category.TRANSACTION_TYPE_INCOME)
        self.assertEqual(displayed_transactions[0].amount, Decimal('200.00'))


        # Transaction t2 (middle)
        self.assertEqual(displayed_transactions[1].pk, self.t2_expense.pk)
        self.assertEqual(displayed_transactions[1].running_balance, Decimal('450.00'))
        self.assertEqual(displayed_transactions[1].category.type, Category.TRANSACTION_TYPE_EXPENSE)
        self.assertEqual(displayed_transactions[1].amount, Decimal('50.00'))

        # Transaction t1 (oldest)
        self.assertEqual(displayed_transactions[2].pk, self.t1_income.pk)
        self.assertEqual(displayed_transactions[2].running_balance, Decimal('500.00'))
        self.assertEqual(displayed_transactions[2].category.type, Category.TRANSACTION_TYPE_INCOME)
        self.assertEqual(displayed_transactions[2].amount, Decimal('500.00'))

        # Test combined view as well (since it's part of the same view logic)
        self.assertIn('combined_transactions_with_balance', context)
        combined_transactions = context['combined_transactions_with_balance']
        self.assertEqual(len(combined_transactions), 3)

        # Check running balances in combined view (should be the same as single safe in this case)
        self.assertEqual(combined_transactions[0].pk, self.t3_income.pk)
        self.assertEqual(combined_transactions[0].running_balance, Decimal('650.00'))
        self.assertEqual(combined_transactions[1].pk, self.t2_expense.pk)
        self.assertEqual(combined_transactions[1].running_balance, Decimal('450.00'))
        self.assertEqual(combined_transactions[2].pk, self.t1_income.pk)
        self.assertEqual(combined_transactions[2].running_balance, Decimal('500.00'))
        
        # Check Category model is passed for template logic
        self.assertIn('Category', context)
        self.assertEqual(context['Category'], Category)


class TransactionPermissionTests(TestCase):
    def setUp(self):
        self.superuser = create_user(username='superuser', is_superuser=True)
        self.regular_user = create_user(username='regularuser')
        
        self.safe = create_safe()
        # Assign safe to both users for simplicity in testing actions
        UserSafeAssignment.objects.create(user=self.superuser, safe=self.safe)
        UserSafeAssignment.objects.create(user=self.regular_user, safe=self.safe)

        self.category = create_category('General', Category.TRANSACTION_TYPE_INCOME)

        self.transaction_yesterday = Transaction.objects.create(
            user=self.regular_user, # or superuser, doesn't matter for ownership here
            safe=self.safe,
            category=self.category,
            amount=Decimal('100.00'),
            transaction_date=timezone.now() - timezone.timedelta(days=1)
        )
        self.transaction_today = Transaction.objects.create(
            user=self.regular_user, # or superuser
            safe=self.safe,
            category=self.category,
            amount=Decimal('200.00'),
            transaction_date=timezone.now()
        )
        
        self.update_url_yesterday = reverse('cashflow:transaction_update', kwargs={'pk': self.transaction_yesterday.pk})
        self.delete_url_yesterday = reverse('cashflow:transaction_delete', kwargs={'pk': self.transaction_yesterday.pk})
        self.update_url_today = reverse('cashflow:transaction_update', kwargs={'pk': self.transaction_today.pk})
        self.delete_url_today = reverse('cashflow:transaction_delete', kwargs={'pk': self.transaction_today.pk})
        
        self.list_url = reverse('cashflow:transaction_list')

    def test_superuser_permissions(self):
        self.client.login(username='superuser', password='password')
        
        # Can access update/delete views for yesterday's transaction
        response_update_get_yesterday = self.client.get(self.update_url_yesterday)
        self.assertEqual(response_update_get_yesterday.status_code, 200)
        response_delete_get_yesterday = self.client.get(self.delete_url_yesterday)
        self.assertEqual(response_delete_get_yesterday.status_code, 200)

        # Can access update/delete views for today's transaction
        response_update_get_today = self.client.get(self.update_url_today)
        self.assertEqual(response_update_get_today.status_code, 200)
        response_delete_get_today = self.client.get(self.delete_url_today)
        self.assertEqual(response_delete_get_today.status_code, 200)

        # Superuser can successfully delete yesterday's transaction
        response_delete_post_yesterday = self.client.post(self.delete_url_yesterday)
        self.assertEqual(response_delete_post_yesterday.status_code, 302) # Redirects to list
        self.assertFalse(Transaction.objects.filter(pk=self.transaction_yesterday.pk).exists())

        # Superuser can successfully update today's transaction (form data would be needed for full update)
        # For simplicity, we'll just check the POST access and redirect
        update_data = {
            'safe': self.safe.pk,
            'transaction_type_selector': self.category.type,
            'category': self.category.pk,
            'amount': Decimal('250.00'), # Changed amount
            'payment_method': Transaction.PAYMENT_METHOD_CASH,
        }
        response_update_post_today = self.client.post(self.update_url_today, data=update_data)
        self.assertEqual(response_update_post_today.status_code, 302) # Redirects
        updated_transaction_today = Transaction.objects.get(pk=self.transaction_today.pk)
        self.assertEqual(updated_transaction_today.amount, Decimal('250.00'))


    def test_regular_user_permissions(self):
        self.client.login(username='regularuser', password='password')

        # Regular user CANNOT access update/delete views for yesterday's transaction (GET)
        response_update_get_yesterday = self.client.get(self.update_url_yesterday)
        self.assertEqual(response_update_get_yesterday.status_code, 302) # Redirect
        self.assertEqual(response_update_get_yesterday.url, self.list_url)
        
        response_delete_get_yesterday = self.client.get(self.delete_url_yesterday)
        self.assertEqual(response_delete_get_yesterday.status_code, 302) # Redirect
        self.assertEqual(response_delete_get_yesterday.url, self.list_url)
        
        # Check for messages (this requires middleware and settings to be right for messages to appear in test client)
        # For now, we'll assume the redirect implies the message was set.
        # A more robust way is to check messages in the response context if available, or use a MessageTestMixin.

        # Regular user CAN access update/delete views for today's transaction (GET)
        response_update_get_today = self.client.get(self.update_url_today)
        self.assertEqual(response_update_get_today.status_code, 200)
        response_delete_get_today = self.client.get(self.delete_url_today)
        self.assertEqual(response_delete_get_today.status_code, 200)

        # Regular user CANNOT delete yesterday's transaction (POST)
        response_delete_post_yesterday = self.client.post(self.delete_url_yesterday)
        self.assertEqual(response_delete_post_yesterday.status_code, 302) # Redirect
        self.assertEqual(response_delete_post_yesterday.url, self.list_url)
        self.assertTrue(Transaction.objects.filter(pk=self.transaction_yesterday.pk).exists()) # Still exists

        # Regular user CANNOT update yesterday's transaction (POST)
        update_data_yesterday = {
            'safe': self.safe.pk,
            'transaction_type_selector': self.category.type,
            'category': self.category.pk,
            'amount': Decimal('150.00'),
            'payment_method': Transaction.PAYMENT_METHOD_CASH,
        }
        response_update_post_yesterday = self.client.post(self.update_url_yesterday, data=update_data_yesterday)
        self.assertEqual(response_update_post_yesterday.status_code, 302) # Redirect
        self.assertEqual(response_update_post_yesterday.url, self.list_url)
        self.transaction_yesterday.refresh_from_db()
        self.assertEqual(self.transaction_yesterday.amount, Decimal('100.00')) # Amount unchanged

        # Regular user CAN successfully delete today's transaction
        # Need to re-create today's transaction as it might have been updated by superuser test if tests run in certain order
        # Best practice: ensure tests are isolated or re-initialize state. For now, we'll assume it's there.
        # If transaction_today was deleted by superuser test, this will fail.
        # Let's ensure it exists or re-create for this specific test path
        if not Transaction.objects.filter(pk=self.transaction_today.pk).exists():
             self.transaction_today = Transaction.objects.create(
                user=self.regular_user, safe=self.safe, category=self.category,
                amount=Decimal('200.00'), transaction_date=timezone.now()
            )
        
        response_delete_post_today = self.client.post(reverse('cashflow:transaction_delete', kwargs={'pk': self.transaction_today.pk}))
        self.assertEqual(response_delete_post_today.status_code, 302) # Redirects
        self.assertFalse(Transaction.objects.filter(pk=self.transaction_today.pk).exists())

        # Regular user CAN successfully update today's transaction
        # Re-create today's transaction if it was deleted above
        self.transaction_today = Transaction.objects.create(
            user=self.regular_user, safe=self.safe, category=self.category,
            amount=Decimal('200.00'), transaction_date=timezone.now()
        )
        update_data_today = {
            'safe': self.safe.pk,
            'transaction_type_selector': self.category.type,
            'category': self.category.pk,
            'amount': Decimal('220.00'),
            'payment_method': Transaction.PAYMENT_METHOD_BANK,
        }
        response_update_post_today = self.client.post(reverse('cashflow:transaction_update', kwargs={'pk': self.transaction_today.pk}), data=update_data_today)
        self.assertEqual(response_update_post_today.status_code, 302) # Redirects
        updated_transaction_today = Transaction.objects.get(pk=self.transaction_today.pk)
        self.assertEqual(updated_transaction_today.amount, Decimal('220.00'))

    def test_current_date_in_list_view_context(self):
        self.client.login(username='regularuser', password='password')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('current_date', response.context)
        self.assertEqual(response.context['current_date'], timezone.now().date())
