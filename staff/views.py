from django.shortcuts import render

# Create your views here.
# staff/views.py
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Staff
from django.contrib.auth.models import User
from services.models import Service
from staff.models import Staff
from appointments.models import Appointment
from django.contrib.auth.decorators import login_required
# staff/views.py
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.http import HttpResponse

def send_simple_email(request):
    subject = "Test Email from Django"
    message = "This is a test email from Django!"
    from_email = "saumusalim.co@gmail.com"  # Must match `EMAIL_HOST_USER`
    recipient_list = ["jojomadready@gmail.com"]  # Add the recipient email here

    send_mail(subject, message, from_email, recipient_list)
    return HttpResponse("Email sent successfully!")



def staff_detail(request, pk):
    # Fetch the staff member by ID
    staff = get_object_or_404(Staff, id=pk)

    # Return JSON response
    data = {
        'id': staff.id,
        'first_name': staff.first_name,
        'last_name': staff.last_name,
        'role': staff.role,
        'commission_rate': str(staff.commission_rate),
    }
    return JsonResponse(data)

def staff_list(request):
    # Query all staff members
    queryset = Staff.objects.all().order_by('id')
    staff_list = Staff.objects.all()
    services = Service.objects.all()
    # Apply role filter
    role_filter = request.GET.get('role', '')  # Default to no filter
    if role_filter:
        queryset = queryset.filter(role=role_filter)

    # Pagination
    page_number = request.GET.get('page', 1)
    entries_per_page = request.GET.get('entries', 10)  # Default to 10 entries per page
    paginator = Paginator(queryset, entries_per_page)

    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    # Check if the request is an AJAX call
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = {
            'staff': [
                {
                    'id': s.id,
                    'first_name': s.first_name,
                    'last_name': s.last_name,
                    'role': s.role,
                    'commission_rate': str(s.commission_rate),
                }
                for s in page_obj.object_list
            ],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        return JsonResponse(data)

    # Render the template for non-AJAX requests
    return render(request, 'reports/staff_report.html', {'staff': page_obj, 'st': 'st', 'services': services, 'staff_list': staff_list})

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def staff_create_update(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        staff_id = data.get('id')

        # Update existing staff member or create a new one
        if staff_id:
            staff = get_object_or_404(Staff, id=staff_id)
        else:
            staff = Staff()

        staff.first_name = data.get('first_name')
        staff.last_name = data.get('last_name')
        staff.role = data.get('role')
        staff.commission_rate = data.get('commission_rate')
        base_username = f"{staff.first_name.lower()}_{staff.last_name.lower()}"
        username = base_username

        # Ensure the username is unique by checking the database
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",  # Default email
            password='defaultpassword',  # Default password (you can change this later)
            first_name=staff.first_name,
            last_name=staff.last_name
        )

        # Link the User instance to the Staff instance
        staff.user = user
        staff.save()
        

        return JsonResponse({'success': True, 'message': 'Staff saved successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})



@csrf_exempt
def staff_delete(request):
    if request.method == 'DELETE':
        data = json.loads(request.body)
        staff_id = data.get('id')
        staff = get_object_or_404(Staff, id=staff_id)
        staff.delete()
        return JsonResponse({'success': True, 'message': 'Staff deleted successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
# def staff_notifications(request):
#     staff = request.user.staff  # Assuming Staff model is linked to User

#     # Determine appointments based on staff role
#     if staff.role == "masseuse":
#         appointments = Appointment.objects.filter(service__category__in=["spa", "massage"], status="pending")
#     elif staff.role == "barber":
#         appointments = Appointment.objects.filter(service__category="haircut", status="pending")
#     else:
#         appointments = Appointment.objects.none()  # No notifications for admin

#     unread_count = appointments.count()

#     notifications = [
#         {
#             "customer": appointment.customer.first_name,
#             "service": appointment.service.name,
#             "date": appointment.appointment_date.strftime("%Y-%m-%d %H:%M"),
#         }
#         for appointment in appointments
#     ]
#     s = Service.objects.get(name='Outline')

#     print(appointments, notifications, unread_count, staff.role, s.category)

#     return JsonResponse({"unread_count": unread_count, "notifications": notifications})

def staff_notifications(request):
    staff_role = request.user.staff.role  # Get logged-in staff role

    if staff_role == "masseuse":
        pending_appointments = Appointment.objects.filter(service__category__in=["spa", "massage"], status="pending")
        confirmed_appointments = Appointment.objects.filter(service__category__in=["spa", "massage"], status="confirmed")
    elif staff_role == "barber":
        pending_appointments = Appointment.objects.filter(service__category="haircut", status="pending")
        confirmed_appointments = Appointment.objects.filter(service__category="haircut", status="confirmed")
    else:
        pending_appointments = confirmed_appointments = Appointment.objects.none()

    print(pending_appointments, confirmed_appointments)

    def serialize_appointments(queryset):
        return [
            {
                "id": appt.id,
                "service_name": appt.service.name,
                "date": appt.appointment_date.strftime("%Y-%m-%d"),
                "time": appt.appointment_date.strftime("%H:%M"),
                "status": appt.status,
            }
            for appt in queryset
        ]

    return JsonResponse({
        "unread_count": pending_appointments.count(),
        "notifications": serialize_appointments(pending_appointments) + serialize_appointments(confirmed_appointments),
    })





def mark_confirmed(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    print('appointment \n \n', appointment)
    if appointment.status == "pending":
        appointment.status = "confirmed"
        appointment.staff = request.user.staff
        appointment.save()
        return JsonResponse({"status": "success", "message": "Appointment marked as confirmed"})
    return JsonResponse({"status": "error", "message": "Appointment could not be confirmed"})

def mark_completed(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    print('appointment \n \n', appointment)
    if appointment.status == "confirmed":
        appointment.status = "completed"
        appointment.save()
        return JsonResponse({"status": "success", "message": "Appointment marked as completed"})
    return JsonResponse({"status": "error", "message": "Appointment could not be completed"})


def get_appointment_details(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        appointment_data = {
            "id": appointment.id,
            "customer_name": appointment.customer.first_name + appointment.customer.last_name,  # Assuming customer has a `name` field
            "staff_id": request.user.staff.id,
            "service_id": appointment.service.id,
            "amount_paid": appointment.service.price,
        }
        return JsonResponse({"status": "success", "appointment": appointment_data})
    except Appointment.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Appointment not found"})