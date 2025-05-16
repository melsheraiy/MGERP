from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.new_contact, name='new_contact'),
    path('list/', views.contacts_list, name='contacts_list'),
    path('view/<int:id>/', views.view_contact, name='view_contact'),
    path('edit/<int:id>/', views.edit_contact, name='edit_contact'),
    path('delete/<int:id>/', views.delete_contact, name='delete_contact'),
]
