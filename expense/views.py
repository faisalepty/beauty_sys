# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Expense, Category, Payment
import json
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now
from django.shortcuts import render, get_object_or_404


from datetime import datetime

@csrf_exempt
def create_update_expense(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            expense_id = data.get('id')  # ID for updates
            category_id = data.get('category_id')
            amount = data.get('amount')
            description = data.get('description', '')
            start_date = data.get('start_date')  # Allow None
            end_date = data.get('end_date')  # Allow None
            recurring_frequency = data.get('recurring_frequency', 'NONE')
            is_paid = data.get('is_paid', False)

            # Debugging: Print raw input dates
            print('Raw Input Dates:', start_date, end_date)

            # Convert start_date and end_date to Python date objects if provided
            try:
                if start_date:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    start_date = None  # Handle empty start_date

                if end_date:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    end_date = None  # Handle empty end_date
            except ValueError as e:
                return JsonResponse({'success': False, 'error': f'Invalid date format: {str(e)}'})

            # Validate required fields
            if not category_id or not amount:
                return JsonResponse({'success': False, 'error': 'Category and amount are required.'})

            category = get_object_or_404(Category, id=category_id)

            if expense_id:
                # Update existing expense
                expense = get_object_or_404(Expense, id=expense_id)
                expense.category = category
                expense.amount = amount
                expense.description = description
                expense.start_date = start_date
                expense.end_date = end_date
                expense.recurring_frequency = recurring_frequency
                expense.is_paid = is_paid
                expense.save()
            else:
                # Create new expense
                Expense.objects.create(
                    category=category,
                    amount=amount,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                    recurring_frequency=recurring_frequency,
                    is_paid=is_paid
                )

            return JsonResponse({'success': True, 'message': 'Expense saved successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
def delete_expense(request):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            expense_id = data.get('id')
            expense = get_object_or_404(Expense, id=expense_id)
            expense.delete()
            return JsonResponse({'success': True, 'message': 'Expense deleted successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
def record_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            expense_id = data.get('expense_id')
            amount_paid = data.get('amount_paid')
            payment_date = data.get('payment_date', now().date())

            # Validate required fields
            if not expense_id or not amount_paid:
                return JsonResponse({'success': False, 'error': 'Expense ID and amount paid are required.'})

            expense = get_object_or_404(Expense, id=expense_id)

            # Create payment record
            Payment.objects.create(
                expense=expense,
                amount_paid=amount_paid,
                payment_date=payment_date
            )

            # Mark expense as paid if fully paid
            total_payments = Payment.objects.filter(expense=expense).aggregate(total=Sum('amount_paid'))['total'] or 0
            if total_payments >= expense.amount:
                expense.is_paid = True
                expense.save()

            return JsonResponse({'success': True, 'message': 'Payment recorded successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

def expense_list(request):
    queryset = Expense.objects.all().order_by('-start_date')

    # Apply filters
    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    page_number = request.GET.get('page', 1)
    entries_per_page = request.GET.get('entries', 10)
    paginator = Paginator(queryset, entries_per_page)

    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = {
            'expenses': [
                {
                    'id': expense.id,
                    'category': expense.category.name,
                    'amount': str(expense.amount),
                    'description': expense.description or '',
                    'start_date': expense.start_date.strftime('%Y-%m-%d'),
                    'end_date': expense.end_date.strftime('%Y-%m-%d') if expense.end_date else None,
                    'recurring_frequency': expense.recurring_frequency,
                    'is_paid': expense.is_paid,
                }
                for expense in page_obj.object_list
            ],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        return JsonResponse(data)

    categories = Category.objects.all()
    return render(request, 'reports/expense_list.html', {
        'expenses': page_obj,
        'categories': categories,
        'selected_category': category_id,
    })

def generate_recurring_expenses():
    today = now().date()
    recurring_expenses = Expense.objects.filter(
        recurring_frequency__in=['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'],
        start_date__lte=today
    ).exclude(end_date__lt=today)

    for expense in recurring_expenses:
        if not expense.last_generated or needs_regeneration(expense, today):
            # Create a new expense entry
            Expense.objects.create(
                category=expense.category,
                amount=expense.amount,
                description=expense.description,
                start_date=today,
                recurring_frequency='NONE',
                is_paid=False
            )
            # Update the last_generated field
            expense.last_generated = today
            expense.save()

def needs_regeneration(expense, today):
    if expense.recurring_frequency == 'DAILY':
        return today > expense.last_generated
    elif expense.recurring_frequency == 'WEEKLY':
        return (today - expense.last_generated).days >= 7
    elif expense.recurring_frequency == 'MONTHLY':
        next_date = expense.last_generated + relativedelta(months=1)
        return today >= next_date
    elif expense.recurring_frequency == 'YEARLY':
        next_date = expense.last_generated + relativedelta(years=1)
        return today >= next_date
    return False