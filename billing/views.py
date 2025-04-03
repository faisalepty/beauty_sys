from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.timezone import now
from django.utils import timezone
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum
from .models import Billing
from appointments.models import Appointment, TaskAssignment
from customers.models import Customer
from staff.models import Staff
from services.models import Service, AdditionalTask
from expense.models import Expense
from .forms import BillingForm
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import json
from django.contrib.auth.decorators import user_passes_test 
from django.http import HttpResponseForbidden # Import HttpResponseForbidden
from django.contrib.auth.decorators import login_required


def is_staff(user):
    return Staff.objects.filter(user=user).exists() or user.is_superuser

def is_staff_member(user):
    """Custom test function to check if a user is a member of the 'staff' group."""
    return user.groups.filter(name='staff').exists() or user.is_superuser

def mpesa_callback(request):
    if request.method == "POST":
        data = json.loads(request.body)
        print("MPESA CALLBACK DATA:", data)
        return JsonResponse({"message": "Callback received"}, status=200)
    return JsonResponse({"error": "Invalid request"}, status=400)

def get_billing(request, billing_id):
    billing = get_object_or_404(Billing, id=billing_id)
    data = {
        'id': billing.id,
        'appointment': {
            'id': billing.appointment.id if billing.appointment else None,
            'customer': {
                'id': billing.appointment.customer.id if billing.appointment and billing.appointment.customer else None,
                'first_name': billing.appointment.customer.first_name if billing.appointment and billing.appointment.customer else '',
                'last_name': billing.appointment.customer.last_name if billing.appointment and billing.appointment.customer else '',
            } if billing.appointment and billing.appointment.customer else None,
            'staff': {
                'id': billing.appointment.staff.id if billing.appointment and billing.appointment.staff else None,
                'first_name': billing.appointment.staff.first_name if billing.appointment and billing.appointment.staff else '',
                'last_name': billing.appointment.staff.last_name if billing.appointment and billing.appointment.staff else '',
            } if billing.appointment and billing.appointment.staff else None,
            'service': {
                'id': billing.appointment.service.id if billing.appointment and billing.appointment.service else None,
                'name': billing.appointment.service.name if billing.appointment and billing.appointment.service else '',
            } if billing.appointment and billing.appointment.service else None,
        } if billing.appointment else None,
        'payment_method': billing.payment_method,
        'amount': str(billing.amount),
        'discount': str(billing.discount or 0),
        'tax': str(billing.tax or 0),
        'total': str(billing.total),
    }
    return JsonResponse(data)

def billing_list(request):
    if not request.user.is_authenticated and not is_staff_member(request.user):
        return HttpResponseForbidden(render(request, 'permission_denied.html')) # Return 403 with error page.

    queryset = Billing.objects.all().order_by('-created_at')
    staff_list = Staff.objects.all()
    services = Service.objects.all()

    payment_method_filter = request.GET.get('payment_method', '')
    if payment_method_filter:
        queryset = queryset.filter(payment_method=payment_method_filter)

    page_number = request.GET.get('page', 1)
    entries_per_page = request.GET.get('entries', 10)
    paginator = Paginator(queryset, entries_per_page)

    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = {
            'billings': [
                {
                    'id': b.id,
                    'appointment_id': b.appointment.id,
                    'service': b.appointment.service.name,
                    'customer_name': f"{b.appointment.customer.first_name} {b.appointment.customer.last_name}"
                                    if b.appointment and b.appointment.customer else "Unknown Customer",
                    'staff_name': f"{b.appointment.staff.first_name} {b.appointment.staff.last_name}"
                                 if b.appointment and b.appointment.staff else "No Staff Assigned",
                    'payment_method': b.payment_method,
                    'amount': str(b.amount or 0),
                    'discount': str(b.discount or 0),
                    'tax': str(b.tax or 0),
                    'total': str(b.total or 0),
                    'status': b.appointment.status,
                    'completion_percentage': b.appointment.completion_percentage,
                    'created_at': b.created_at.date(),
                }
                for b in page_obj.object_list
            ],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        return JsonResponse(data)

    return render(request, 'reports/billing_report.html', {
        'billings': page_obj,
        's': 's',
        'staff_list': staff_list,
        'services': services,
    })

@csrf_exempt
def update_billing(request):
    if request.method == 'POST':
        billing_id = request.POST.get('id')
        appointment_id = request.POST.get('appointmentId')
        customer_name = request.POST.get('walkin_customer_name')
        staff_id = request.POST.get('walkin_staff_name')
        service_id = request.POST.get('walkin_service')
        amount_paid = request.POST.get('walkin_amount_paid')

        if not customer_name or not staff_id or not service_id or not amount_paid:
            return JsonResponse({'success': False, 'error': 'Please fill out all required fields.'})

        staff = get_object_or_404(Staff, id=staff_id)
        service = get_object_or_404(Service, id=service_id)

        first_name, last_name = customer_name.split(' ', 1) if ' ' in customer_name else (customer_name, '')
        customer, created = Customer.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            defaults={'email': f'{customer_name.replace(" ", ".")}@example.com', 'phone_number': 'N/A'}
        )

        if billing_id or appointment_id:
            
            
            if billing_id:
                billing = get_object_or_404(Billing, id=billing_id)
                appointment = billing.appointment
                appointment.customer = customer
                appointment.staff = staff
                appointment.service = service
                appointment.save()
                billing.amount = amount_paid
                billing.total = amount_paid
                billing.save()
            else:
                appointment = get_object_or_404(Appointment, id=appointment_id)
                appointment.status = 'completed'
                appointment.save()
                Billing.objects.create(
                appointment=appointment,
                payment_method='cash',
                amount=amount_paid,
                discount=0,
                tax=0,
                total=amount_paid
            )
           
        else:
            appointment = Appointment.objects.create(
                customer=customer,
                service=service,
                staff=staff,
                appointment_date=now(),
                status='completed'
            )
            Billing.objects.create(
                appointment=appointment,
                payment_method='cash',
                amount=amount_paid,
                discount=0,
                tax=0,
                total=amount_paid
            )

        return JsonResponse({'success': True, 'message': 'Billing record saved successfully.'})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

def get_additional_tasks(request, service_id):
    try:
        service = Service.objects.get(id=service_id)
        tasks = service.additional_tasks.all()
        task_data = [
            {
                'id': task.id,
                'name': task.name,
                'fixed_price': str(task.fixed_price),
            }
            for task in tasks
        ]
        return JsonResponse({'success': True, 'tasks': task_data})
    except Service.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Service not found.'})

@csrf_exempt
def create_update_billing(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            billing_id = data.get('id')
            customer_name = data.get('customer_name')
            services = data.get('services')
            additional_charges = Decimal(data.get('additional_charges', '0'))

            if not services:
                return JsonResponse({'success': False, 'error': 'Please fill out all required fields.'})
            if not customer_name:
                customer = Customer.objects.filter(first_name="faisal").first()
            else:
                first_name, last_name = customer_name.split(' ', 1) if ' ' in customer_name else (customer_name, '')
                customer, created = Customer.objects.get_or_create(
                    first_name=first_name,
                    last_name=last_name,
                    defaults={'email': f'{customer_name.replace(" ", ".")}@example.com', 'phone_number': 'N/A'}
                )

            total_amount = Decimal('0')

            if billing_id:
                billing_records = Billing.objects.filter(id=billing_id)
                if not billing_records.exists():
                    return JsonResponse({'success': False, 'error': 'Billing record not found.'})
                Appointment.objects.filter(billing__id=billing_id).delete()
                TaskAssignment.objects.filter(appointment__billing__id=billing_id).delete()

            for service_data in services:
                service = get_object_or_404(Service, id=service_data['service_id'])
                staff = get_object_or_404(Staff, id=service_data['staff_id'])
                amount_paid = Decimal(service_data['amount_paid'])

                total_amount += amount_paid

                appointment = Appointment.objects.create(
                    customer=customer,
                    service=service,
                    staff=staff,
                    appointment_date=now(),
                    status='completed'
                )

                additional_tasks = service.additional_tasks.all()
                for task in additional_tasks:
                    task_staff_id = service_data.get(f'task_{task.id}_staff_id')
                    if task_staff_id:
                        task_staff = get_object_or_404(Staff, id=task_staff_id)
                        TaskAssignment.objects.create(
                            appointment=appointment,
                            staff=task_staff,
                            additional_task=task
                        )

                if billing_id:
                    billing = Billing.objects.get(id=billing_id)
                    billing.appointment = appointment
                    billing.payment_method = 'cash'
                    billing.amount = amount_paid
                    billing.discount = Decimal(service_data['discount'])
                    billing.tax = Decimal('0')
                    billing.total = amount_paid
                    billing.save()
                else:
                    Billing.objects.create(
                        appointment=appointment,
                        payment_method='cash',
                        amount=amount_paid,
                        discount=Decimal(service_data['discount']),
                        tax=Decimal('0'),
                        total=amount_paid
                    )

            total_amount += additional_charges

            return JsonResponse({'success': True, 'message': 'Billing records saved successfully.'})
        except Exception as e:
            print({'error': str(e)})
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
def delete_billing(request):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            billing_id = data.get('id')
            billing = get_object_or_404(Billing, id=billing_id)
            appointment = billing.appointment
            billing.delete()
            appointment.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def mark_as_transacted(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            billing_id = data.get('id')
            billing = get_object_or_404(Billing, id=billing_id)
            appointment = get_object_or_404(Appointment, id=billing.appointment.id)
            appointment.status = 'transacted'
            appointment.save()
            print('success \n \n \n \n', billing.appointment.id)
            return JsonResponse({'success': True})
        except Exception as e:
            print('error \n \n \n \n', e)
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def staff_sales(request, pk=None):

    if not request.user.is_authenticated and not is_staff(request.user):
        return HttpResponseForbidden(render(request, 'permission_denied.html')) # Return 403 with error page.
    staff_list = Staff.objects.all()
    services = Service.objects.all()
    if pk:
        staff = Staff.objects.get(pk=pk)
        context = {'staff': staff, 'sts1': 'sts1', 'staff_list': staff_list,
        'services': services}
    else:
        staff = Staff.objects.get(user=request.user)
        context = {'staff': staff, 'sts': 'sts', 'staff_list': staff_list,
        'services': services}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        queryset = get_staff_appointments_and_tasks(staff, request.GET)
        page_number = request.GET.get('page', 1)
        entries_per_page = request.GET.get('entries', 10)
        paginator = Paginator(queryset, entries_per_page)

        try:
            page_obj = paginator.page(page_number)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.page(1)

        data = {
            'appointments': [
                {
                    'id': item['appointment'].id,
                    'customer_name': f"{item['appointment'].customer.first_name} {item['appointment'].customer.last_name}",
                    'staff_name': f"{staff.first_name} {staff.last_name}",
                    'payment_method': item['appointment'].billing.payment_method if hasattr(item['appointment'], 'billing') else 'N/A',
                    'amount_paid': str(item['amount_paid']),
                    'date': item['appointment'].created_at.date(),
                    'status': item['appointment'].status,
                    'is_additional_task': item['is_additional_task'],
                    'main_task': item['appointment'].service.name if item['is_additional_task'] else "",
                    'task_name': item['task_name'] if item['is_additional_task'] else item['appointment'].service.name,
                }
                for item in page_obj.object_list
            ],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        print(data)
        return JsonResponse(data)

    return render(request, 'reports/staff_sales.html', context)

def get_staff_appointments_and_tasks(staff, filters):
    appointments = Appointment.objects.filter(staff=staff).order_by('-appointment_date')
    status_filter = filters.get('status', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)

    results = []
    for appointment in appointments:
        amount_paid = calculate_payment(appointment, staff)
        results.append({
            'appointment': appointment,
            'amount_paid': amount_paid,
            'is_additional_task': False,
            'task_name': None,
        })

        additional_tasks = TaskAssignment.objects.filter(staff=staff, additional_task__isnull=False)
        count = 0
        for task_assignment in additional_tasks:
            task_amount_paid = task_assignment.additional_task.fixed_price
            print(task_amount_paid, '\n \n \n')
            results.append({
                'appointment': task_assignment.appointment,
                'amount_paid': task_amount_paid,
                'is_additional_task': True,
                'task_name': task_assignment.additional_task.name,
            })
            print(count)

    return results

def calculate_payment(appointment, staff):
    billing = getattr(appointment, 'billing', None)
    if not billing:
        return Decimal('0')
    return billing.total * Decimal('0.4')

def get_revenue_and_profit_last_seven_months():
    today = timezone.now().date()
    data = []
    for i in range(6, -1, -1):
        start_of_month = (today.replace(day=1) - relativedelta(months=i))
        if i == 0:
            end_of_month = today + timedelta(days=1) - timedelta(seconds=1)
        else:
            end_of_month = (start_of_month + relativedelta(months=1) - timedelta(days=1))

        start_of_month = timezone.make_aware(datetime.combine(start_of_month, datetime.min.time()))
        end_of_month = timezone.make_aware(datetime.combine(end_of_month, datetime.max.time()))

        total_revenue = Billing.objects.filter(
            created_at__range=(start_of_month, end_of_month)
        ).filter(appointment__status__in=['completed', 'transacted']).aggregate(total=Sum('total'))['total'] or 0
        current_month_paid_expenses = Expense.objects.filter(
        start_date__range=(start_of_month, end_of_month), is_paid=True).aggregate(total=Sum('amount'))['total'] or 0

        total_profit = (int(total_revenue) * 0.6) - int(current_month_paid_expenses)

        data.append({
            'month': start_of_month.strftime('%b'),
            'revenue': float(total_revenue),
            'profit': float(total_profit)
        })
    return data

def get_service_performance():
    service_performance = Billing.objects.values('appointment__service__name')[:5].annotate(
        total_revenue=Sum('total')
    )
    data = [
        {
            'service': item['appointment__service__name'],
            'revenue': float(item['total_revenue'])
        }
        for item in service_performance
    ]
    return data

def calculate_percentage_change(current, previous):
    if previous == 0 and current == 0:
        return 0
    if previous == 0:
        return 100 if current > 0 else 0
    change = ((current - previous) / previous) * 100
    return round(change, 2)


def dashboard(request):
    # Permission check: Ensure user is authenticated and a staff member
    if not request.user.is_authenticated or not is_staff_member(request.user):
        return HttpResponseForbidden(render(request, 'permission_denied.html'))  # Return 403 with error page.

    # Fetch all appointments with related customer, staff, and billing information
    appointments = Appointment.objects.select_related('customer', 'staff', 'billing').filter(
        status__in=['completed', 'transacted']
    )
    
    # Fetch all staff and service data
    staff_list = Staff.objects.all()
    services = Service.objects.all()

    # Date calculations for today, yesterday, and month-related periods
    today = timezone.now()
    start_of_day = timezone.make_aware(timezone.datetime.combine(today.date(), timezone.datetime.min.time()))
    end_of_day = timezone.make_aware(timezone.datetime.combine(today.date(), timezone.datetime.max.time()))
    start_of_yesterday = timezone.make_aware(timezone.datetime.combine((today - timedelta(days=1)).date(), timezone.datetime.min.time()))
    end_of_yesterday = timezone.make_aware(timezone.datetime.combine((today - timedelta(days=1)).date(), timezone.datetime.max.time()))

    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month = start_of_month - timedelta(days=1)
    start_of_last_month = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_last_month = start_of_month - timedelta(seconds=1)

    # Current month's sales count
    current_month_sales = Billing.objects.filter(
        created_at__range=(start_of_month, end_of_day),
    ).count()
    
    # Last month's sales count
    last_month_sales = Billing.objects.filter(
        created_at__range=(start_of_last_month, end_of_last_month),
    ).count()

    # Calculate the change in monthly sales and its absolute value
    monthly_sales_change = int(current_month_sales) - int(last_month_sales)
    monthly_sales_change_abs = abs(monthly_sales_change) if monthly_sales_change != 0 else 0

    # Today's revenue and profit
    todays_revenue = Billing.objects.filter(
        created_at__range=(start_of_day, end_of_day), appointment__status='transacted'
    ).aggregate(total=Sum('total'))['total'] or 0
    todays_profit = round(Decimal(todays_revenue) * Decimal('0.6'), 2) if todays_revenue else 0
    appointments_today = Appointment.objects.filter(
        created_at__range=(start_of_day, end_of_day), status__in=['transacted', 'completed']
    ).count()

    # Yesterday's revenue and profit
    yesterdays_revenue = Billing.objects.filter(
        created_at__range=(start_of_yesterday, end_of_yesterday), appointment__status='transacted'
    ).aggregate(total=Sum('total'))['total'] or 0
    yesterdays_profit = round(Decimal(yesterdays_revenue) * Decimal('0.6'), 2) if yesterdays_revenue else 0
    appointments_yesterday = Appointment.objects.filter(
        created_at__range=(start_of_yesterday, end_of_yesterday)
    ).count()




       # Current month's expenses
    current_month_paid_expenses = Expense.objects.filter(
        start_date__range=(start_of_month, end_of_day),
        is_paid=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    current_month_unpaid_expenses = Expense.objects.filter(
        start_date__range=(start_of_month, end_of_day),
        is_paid=False
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Last month's expenses
    last_month_paid_expenses = Expense.objects.filter(
        start_date__range=(start_of_last_month, end_of_last_month),
        is_paid=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    last_month_unpaid_expenses = Expense.objects.filter(
        start_date__range=(start_of_last_month, end_of_last_month),
        is_paid=False
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Total expenses for the current month
    total_current_month_expenses = current_month_paid_expenses + current_month_unpaid_expenses
    total_last_month_expenses = last_month_paid_expenses + last_month_unpaid_expenses





    # Current month revenue and profit
    current_month_revenue_g = Billing.objects.filter(
        created_at__range=(start_of_month, end_of_day),
    ).aggregate(total=Sum('total'))['total']
    current_month_revenue = int(current_month_revenue_g if current_month_revenue_g is not None else 0)
    current_month_profit = round((Decimal(current_month_revenue) * Decimal('0.6')) - Decimal(current_month_paid_expenses), 2) if current_month_revenue else 0

    # Last month revenue and profit
    last_month_revenue = Billing.objects.filter(
        created_at__range=(start_of_last_month, end_of_last_month),
    ).aggregate(total=Sum('total'))['total'] or 0
    last_month_profit = round(Decimal(last_month_revenue) * Decimal('0.6'), 2) if last_month_revenue else 0

    # Total revenue and profit for all time
    total_revenue = Billing.objects.filter(appointment__status__in=['transacted', 'completed']).aggregate(total=Sum('total'))['total'] or 0
    total_profit = round(Decimal(total_revenue) * Decimal('0.6'), 2) if total_revenue else 0
    total_appointments = Appointment.objects.count()

    # Percentage change calculations
    def calculate_percentage_change(current_value, previous_value):
        if previous_value == 0:
            return 0
        return ((current_value - previous_value) / previous_value) * 100




    todays_revenue_change = calculate_percentage_change(todays_revenue, yesterdays_revenue)
    todays_profit_change = calculate_percentage_change(todays_profit, yesterdays_profit)
    total_revenue_change = calculate_percentage_change(total_revenue, yesterdays_revenue)
    current_month_revenue_change = calculate_percentage_change(current_month_revenue, last_month_revenue)
    current_month_profit_change = calculate_percentage_change(current_month_profit, last_month_profit)
    total_appointments_change = calculate_percentage_change(total_appointments, appointments_yesterday)
    paid_expenses_change = calculate_percentage_change(current_month_paid_expenses, last_month_paid_expenses)
    unpaid_expenses_change = calculate_percentage_change(current_month_unpaid_expenses, last_month_unpaid_expenses)
    total_expenses_change = calculate_percentage_change(total_current_month_expenses, total_last_month_expenses)



    # Appointment change data
    appointments_today_change = appointments_today - appointments_yesterday
    appointments_today_change_abs = abs(appointments_today_change) if appointments_today_change != 0 else 0

    # Get additional data for revenue and service performance
    revenue_data = get_revenue_and_profit_last_seven_months()
    service_performance = get_service_performance()

    # Render the dashboard page
    return render(request, 'reports/admin_dashboard.html', {
        'appointments': appointments,
        'staff_list': staff_list,
        'services': services,
        'current_month_sales': current_month_sales,
        'monthly_sales_change': monthly_sales_change,
        'monthly_sales_change_abs': monthly_sales_change_abs,
        'current_month_revenue': current_month_revenue,
        'current_month_profit': current_month_profit,
        'todays_revenue': todays_revenue,
        'total_revenue': round(total_revenue, 2),
        'todays_profit': todays_profit,
        'total_profit': total_profit,
        'appointments_today': appointments_today,
        'total_appointments': total_appointments,
        'revenue_data': revenue_data,
        'service_performance': service_performance,
        'd': 'd',
        'todays_revenue_change': round(todays_revenue_change, 2),
        'todays_profit_change': round(todays_profit_change, 2),
        'appointments_today_change': round(appointments_today_change, 2),
        'appointments_today_change_abs': round(appointments_today_change_abs, 2),
        'total_revenue_change': round(total_revenue_change, 2),
        'current_month_revenue_change': round(current_month_revenue_change, 2),
        'current_month_profit_change': round(current_month_profit_change, 2),
        'total_appointments_change': round(total_appointments_change, 2),

        'current_month_paid_expenses': current_month_paid_expenses,
        'current_month_unpaid_expenses': current_month_unpaid_expenses,
        'paid_expenses_change': round(paid_expenses_change, 2),
        'unpaid_expenses_change': round(unpaid_expenses_change, 2),
        'total_current_month_expenses': total_current_month_expenses,
        'paid_expenses_change_abs': abs(round(paid_expenses_change, 2)),
        'total_expenses_change_abs': abs(round(total_expenses_change, 2)),
    })


def sales_list(request):
    if not request.user.is_authenticated and not is_staff_member(request.user):
        return HttpResponseForbidden(render(request, 'permission_denied.html')) # Return 403 with error page.

    staff_list = Staff.objects.all()
    services = Service.objects.all()
    status_filter = request.GET.get('status', 'completed,transacted')
    statuses = [status.strip() for status in status_filter.split(',') if status.strip() and status.strip().lower() != 'none']

    if not statuses:
        statuses = ['completed', 'transacted']

    print("statuses:", statuses)

    appointments = Appointment.objects.filter(status__in=statuses).select_related('customer', 'staff', 'billing').order_by('-created_at')

    print("Filtered Appointments:", appointments)

    page_number = request.GET.get('page', 1)
    entries_per_page = request.GET.get('entries', 10)
    paginator = Paginator(appointments, entries_per_page)
    page_obj = paginator.get_page(page_number)

    print("Paginated Appointments:", page_obj.object_list)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = {
            'appointments': [
                {
                    'id': appt.id,
                    'date': appt.created_at.date(),
                    'customer_name': f"{appt.customer.first_name} {appt.customer.last_name}",
                    'staff_name': f"{appt.staff.first_name} {appt.staff.last_name}",
                    'amount_paid': str(appt.billing.total) if hasattr(appt, 'billing') and appt.billing else "0.00",
                    'completion_percentage': appt.completion_percentage,
                    'status': appt.status,
                }
                for appt in page_obj.object_list
            ],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        print("JSON Response Data:", data)
        return JsonResponse(data)

    return render(request, 'reports/sales_report.html', {
        'appointments': page_obj,
        'statuses': ['completed', 'transacted'],
        'staff_list': staff_list,
        'services': services,
        's': 's',
    })

def add_walkin_appointment(request):
    if request.method == 'POST':
        print("success1")
        customer_name = request.POST.get('walkin_customer_name')
        staff_id = request.POST.get('walkin_staff_name')
        service_id = request.POST.get('walkin_service')
        amount_paid = request.POST.get('walkin_amount_paid')

        if not customer_name or not staff_id or not service_id or not amount_paid:
            print("error", "amount_paid:", amount_paid, "service_id:", service_id, "customer_name:", customer_name, "staff_id:", staff_id)
            return JsonResponse({'success': False, 'error': 'Please fill out all required fields.'})

        staff = get_object_or_404(Staff, id=staff_id)
        service = get_object_or_404(Service, id=service_id)

        first_name, last_name = customer_name.split(' ', 1) if ' ' in customer_name else (customer_name, '')
        customer, created = Customer.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            defaults={'email': f'{customer_name.replace(" ", ".")}@example.com', 'phone_number': 'N/A'}
        )

        appointment = Appointment.objects.create(
            customer=customer,
            service=service,
            staff=staff,
            appointment_date=now(),
            status='completed'
        )

        Billing.objects.create(
            appointment=appointment,
            payment_method='cash',
            amount=amount_paid,
            discount=0,
            tax=0,
            total=amount_paid
        )
        print("success")
        return JsonResponse({'success': True, 'message': 'Walk-in appointment added successfully.'})
    print("error")
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

def update_appointment(request, appointment_id):
    if request.method == 'POST' or request.method == 'PUT':
        appointment = get_object_or_404(Appointment, id=appointment_id)

        customer_name = request.POST.get('walkin_customer_name')
        staff_id = request.POST.get('walkin_staff_name')
        service_id = request.POST.get('walkin_service')
        amount_paid = request.POST.get('walkin_amount_paid')

        if not customer_name or not staff_id or not service_id or not amount_paid:
            return JsonResponse({'success': False, 'error': 'Please fill out all required fields.'})

        first_name, last_name = customer_name.split(' ', 1) if ' ' in customer_name else (customer_name, '')
        customer, created = Customer.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            defaults={'email': f'{customer_name.replace(" ", ".")}@example.com', 'phone_number': 'N/A'}
        )
        appointment.customer = customer
        appointment.staff = get_object_or_404(Staff, id=staff_id)
        appointment.service = get_object_or_404(Service, id=service_id)
        appointment.save()

        billing = getattr(appointment, 'billing', None)
        if billing:
            billing.amount = amount_paid
            billing.total = amount_paid
            billing.save()
        else:
            Billing.objects.create(
                appointment=appointment,
                payment_method='cash',
                amount=amount_paid,
                discount=0,
                tax=0,
                total=amount_paid
            )

        return JsonResponse({'success': True, 'message': 'Appointment updated successfully.'})

def delete_appointment(request, appointment_id):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, id=appointment_id)
        print(appointment)
        appointment.delete()
        return JsonResponse({'success': True, 'message': 'Appointment deleted successfully.'})

def get_appointment_details(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    return JsonResponse({
        'id': appointment.id,
        'customer_name': f"{appointment.customer.first_name} {appointment.customer.last_name}",
        'staff_id': appointment.staff.id,
        'service_id': appointment.service.id,
        'amount_paid': appointment.billing.total if hasattr(appointment, 'billing') else 0,
    })

@login_required
def make_payment(request, appointment_pk):
    appointment = get_object_or_404(Appointment, pk=appointment_pk)

    if request.method == 'POST':
        form = BillingForm(request.POST)
        if form.is_valid():
            billing = form.save(commit=False)
            billing.appointment = appointment

            redeemed_points = int(request.POST.get('redeemed_points', 0))
            if redeemed_points > 0:
                success = appointment.customer.redeem_loyalty_points(redeemed_points)
                if success:
                    billing.amount -= redeemed_points

            billing.total = billing.amount - (billing.discount or 0) + (billing.tax or 0)
            billing.save()
            return redirect('payment_confirmation')
    else:
        form = BillingForm()

    return render(request, 'billing/make_payment.html', {
        'form': form,
        'appointment': appointment,
        'customer': appointment.customer
    })

@login_required
def payment_confirmation(request):
    return render(request, 'billing/payment_confirmation.html')

def get_staff_dashboard_data(user):
    today = timezone.now()
    start_of_day = timezone.make_aware(timezone.datetime.combine(today.date(), timezone.datetime.min.time()))
    end_of_day = timezone.make_aware(timezone.datetime.combine(today.date(), timezone.datetime.max.time()))
    start_of_yesterday = timezone.make_aware(timezone.datetime.combine((today - timedelta(days=1)).date(), timezone.datetime.min.time()))
    end_of_yesterday = timezone.make_aware(timezone.datetime.combine((today - timedelta(days=1)).date(), timezone.datetime.max.time()))

    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month = start_of_month - timedelta(days=1)
    start_of_last_month = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_last_month = start_of_month - timedelta(seconds=1)

    if hasattr(user, 'staff'):
        appointments = Appointment.objects.filter(staff=user.staff)
    else:
        return {}

    additional_tasks_g = TaskAssignment.objects.filter(
        staff__user=user,
        additional_task__isnull=False
    ).aggregate(total=Sum('additional_task__fixed_price'))['total'] or 0
    additional_tasks = int(additional_tasks_g if additional_tasks_g is not None else 0)

    additional_tasks1 = TaskAssignment.objects.filter(
        staff__user=user,
        additional_task__isnull=False
    )
    print('additional_tasks \n \n \n:', additional_tasks1)

    additional_monthly_tasks_g = TaskAssignment.objects.filter(
        staff__user=user,
        appointment__created_at__range=(start_of_month, end_of_day),
        additional_task__isnull=False
    ).aggregate(total=Sum('additional_task__fixed_price'))['total'] or 0
    additional_monthly_tasks = int(additional_monthly_tasks_g if additional_monthly_tasks_g is not None else 0)

    additional_last_month_tasks_g = TaskAssignment.objects.filter(
        staff__user=user,
        appointment__created_at__range=(start_of_last_month, end_of_last_month),
        additional_task__isnull=False
    ).aggregate(total=Sum('additional_task__fixed_price'))['total'] or 0
    additional_last_month_tasks = int(additional_last_month_tasks_g if additional_last_month_tasks_g is not None else 0)

    current_month_payout_g = Billing.objects.filter(
        appointment__staff__user=user,
        created_at__range=(start_of_month, end_of_day),
    ).aggregate(total=Sum('total'))['total']
    current_month_payout = (int(current_month_payout_g if current_month_payout_g is not None else 0) * 0.4) + additional_monthly_tasks or 0

    last_month_payout_g = Billing.objects.filter(
        appointment__staff__user=user,
        created_at__range=(start_of_last_month, end_of_last_month),
    ).aggregate(total=Sum('total'))['total']
    last_month_payout = (int(last_month_payout_g if last_month_payout_g is not None else 0) * 0.4) + additional_last_month_tasks or 0

    print('additional_tasks \n \n \n:', current_month_payout)

    current_month_clients = Appointment.objects.filter(
        staff=user.staff,
        created_at__range=(start_of_month, end_of_day)
    ).count()

    last_month_clients = Appointment.objects.filter(
        staff=user.staff,
        created_at__range=(start_of_last_month, end_of_last_month)
    ).count()

    current_month_revenue_g = Billing.objects.filter(
        appointment__staff__user=user,
        created_at__range=(start_of_month, end_of_day),
    ).aggregate(total=Sum('total'))['total']
    current_month_revenue = int(current_month_revenue_g if current_month_revenue_g is not None else 0)

    last_month_revenue_g = Billing.objects.filter(
        appointment__staff__user=user,
        created_at__range=(start_of_last_month, end_of_last_month),
    ).aggregate(total=Sum('total'))['total']
    last_month_revenue = int(last_month_revenue_g if last_month_revenue_g is not None else 0)

    total_clients = Appointment.objects.filter(
        staff=user.staff
    ).count()

    total_clients_yesterday = Appointment.objects.filter(
        staff=user.staff,
        created_at__range=(start_of_yesterday, end_of_yesterday)
    ).count()

    current_month_revenue_change = calculate_percentage_change(current_month_revenue, last_month_revenue)
    current_month_clients_change = current_month_clients - last_month_clients
    current_month_clients_change_abs = abs(current_month_clients_change) if current_month_clients_change != 0 else 0
    current_month_payout_change = calculate_percentage_change(current_month_payout, last_month_payout)
    total_clients_change = calculate_percentage_change(total_clients, total_clients_yesterday)

    def get_staff_revenue_and_profit_last_seven_months():
        data = []
        today = timezone.now().date()
        for i in range(6, -1, -1):
            start_of_month = (today.replace(day=1) - relativedelta(months=i))
            end_of_month = (start_of_month + relativedelta(months=1) - timedelta(days=1))

            start_of_month = timezone.make_aware(timezone.datetime.combine(start_of_month, timezone.datetime.min.time()))
            end_of_month = timezone.make_aware(timezone.datetime.combine(end_of_month, timezone.datetime.max.time()))

            total_revenue = Billing.objects.filter(
                appointment__staff__user=user,
                created_at__range=(start_of_month, end_of_month),
            ).aggregate(total=Sum('total'))['total'] or 0

            current_month_revenue_d = Billing.objects.filter(
                appointment__staff__user=user,
                created_at__range=(start_of_month, end_of_month),
            ).aggregate(total=Sum('total'))['total'] or 0

            total_d = Billing.objects.filter(
                appointment__staff__user=user,
                created_at__range=(start_of_month, end_of_month),
            ).aggregate(total=Sum('total'))['total'] or 0

            total_tasks_d = TaskAssignment.objects.filter(
                staff__user=user,
                appointment__created_at__range=(start_of_month, end_of_month),
                additional_task__isnull=False
            ).aggregate(total=Sum('additional_task__fixed_price'))['total']

            additional_monthly_tasks_d = int(total_tasks_d if total_tasks_d is not None else 0)

            current_month_payout_d = (int(total_d) * 0.4) + additional_monthly_tasks_d or 0

            total_profit = int(total_revenue) * 0.6

            data.append({
                'month': start_of_month.strftime('%b'),
                'revenue': float(current_month_revenue_d),
                'payout': float(current_month_payout_d)
            })
        return data

    def get_staff_service_performance():
        service_performance = Billing.objects.filter(
            appointment__staff__user=user
        ).values('appointment__service__name')[:5].annotate(
            total_revenue=Sum('total')
        )
        data = [
            {
                'service': item['appointment__service__name'],
                'revenue': float(item['total_revenue'])
            }
            for item in service_performance
        ]
        return data

    revenue_data = get_staff_revenue_and_profit_last_seven_months()
    service_performance = get_staff_service_performance()

    return {
        'current_month_revenue': round(current_month_revenue, 2),
        'current_month_clients': current_month_clients,
        'current_month_payout': round(current_month_payout, 2),
        'total_clients': total_clients,
        'revenue_data': revenue_data,
        'service_performance': service_performance,
        'current_month_revenue_change': current_month_revenue_change,
        'current_month_clients_change': current_month_clients_change,
        'current_month_clients_change_abs': current_month_clients_change_abs,
        'current_month_payout_change': current_month_payout_change,
        'total_clients_change': total_clients_change,
    }

def staff_dashboard(request, pk=None):
    if not request.user.is_authenticated and not is_staff(request.user):
        return HttpResponseForbidden(render(request, 'permission_denied.html')) # Return 403 with error page.
    staff_list = Staff.objects.all()
    services = Service.objects.all()
    if pk:
        staff = Staff.objects.get(pk=pk)
        dashboard_data = get_staff_dashboard_data(staff.user)
    else:
        staff = None
        dashboard_data = get_staff_dashboard_data(request.user)

    return render(request, 'reports/staff_dashboard.html', {
        'staff_list': staff_list,
        'services': services,
        'current_month_revenue': dashboard_data.get('current_month_revenue', 0),
        'current_month_clients': dashboard_data.get('current_month_clients', 0),
        'current_month_payout': dashboard_data.get('current_month_payout', 0),
        'total_clients': dashboard_data.get('total_clients', 0),
        'revenue_data': dashboard_data.get('revenue_data', []),
        'service_performance': dashboard_data.get('service_performance', []),
        'staff': staff,
        'x': 'x',
        'd': "d",
        'current_month_revenue_change': dashboard_data.get('current_month_revenue_change', 0),
        'current_month_clients_change': dashboard_data.get('current_month_clients_change', 0),
        'current_month_clients_change_abs': dashboard_data.get('current_month_clients_change_abs', 0),
        'current_month_payout_change': dashboard_data.get('current_month_payout_change', 0),
        'total_clients_change': dashboard_data.get('total_clients_change', 0),
    })
