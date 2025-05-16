from django.shortcuts import render, redirect, get_object_or_404
from .models import Contact
from .forms import ContactForm

def index(request):
    return render(request, 'contacts/index.html')

def new_contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contacts_list')
    else:
        form = ContactForm()
    return render(request, 'contacts/new_contact.html', {'form': form})

def contacts_list(request):
    contacts = Contact.objects.all()
    return render(request, 'contacts/contacts_list.html', {'contacts': contacts})

def view_contact(request, id):
    contact = get_object_or_404(Contact, id=id)
    return render(request, 'contacts/view_contact.html', {'contact': contact})

def edit_contact(request, id):
    contact = get_object_or_404(Contact, id=id)
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            return redirect('contacts_list')
    else:
        form = ContactForm(instance=contact)
    return render(request, 'contacts/edit_contact.html', {'form': form, 'contact': contact})

def delete_contact(request, id):
    contact = get_object_or_404(Contact, id=id)
    if request.method == 'POST':
        contact.delete()
        return redirect('contacts_list')
    return render(request, 'contacts/delete_contact.html', {'contact': contact})
