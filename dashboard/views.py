from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # Define available apps as a list of dictionaries.
    apps = [
        {'name': 'Sales', 'icon': 'sales_icon.png', 'url': '/sales/'},
        {'name': 'Accounting', 'icon': 'accounting_icon.png', 'url': '/accounting/'},
        {'name': 'Contacts', 'icon': 'contacts_icon.png', 'url': '/contacts/'},
        {'name': 'Salaries', 'icon': 'salaries_icon.png', 'url': '/salaries/'},
        {'name': 'Spare Parts', 'icon': 'spare_parts_icon.png', 'url': '/spareparts/'},
    ]
    return render(request, 'dashboard/dashboard.html', {'apps': apps})
