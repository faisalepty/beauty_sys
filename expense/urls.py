# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Expense List View (with filters, pagination, and AJAX support)
    path('list/', views.expense_list, name='expense_list'),

    # Create/Update Expense (AJAX-based)
    path('create-update/', views.create_update_expense, name='create_update_expense'),

    # Record Payment for an Expense (AJAX-based)
    path('record-payment/', views.record_payment, name='record_payment'),

    # Fetch Details of an Expense for Editing (AJAX-based)
    # path('get-details/<int:expense_id>/', views.get_expense_details, name='get_expense_details'),

    path('delete/', views.delete_expense, name='delete_expense'),

    # Recurring Expense Generation (Scheduled Task Endpoint)
    path('generate-recurring/', views.generate_recurring_expenses, name='generate_recurring_expenses'),
]