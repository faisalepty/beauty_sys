from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.timezone import make_aware
from datetime import datetime
from .models import Appointment
from services.models import Service
from staff.models import Staff
from customers.models import Customer

def home(request):
    services = Service.objects.all()[:3]
    context = {'featured_services': services}
    return render(request, '3_home.html', {'featured_services': services})

# def book_appointment(request):
#     if request.method == 'POST':
#         print("Request POST Data:", request.POST)  # Keeping original debug print
        
#         # Extract form data
#         service_id = request.POST.get('service_id')
#         date = request.POST.get('date')
#         time = request.POST.get('time')

#         # Validate required fields
#         if not service_id or not date or not time:
#             return JsonResponse({'success': False, 'error': 'Please fill out all required fields.'})

#         # Parse datetime
#         try:
#             appointment_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
#             appointment_datetime = make_aware(appointment_datetime)
#         except ValueError:
#             return JsonResponse({'success': False, 'error': 'Invalid date or time format.'})

#         # Fetch service
#         try:
#             service = Service.objects.get(id=service_id)
#         except Service.DoesNotExist:
#             return JsonResponse({'success': False, 'error': 'The selected service does not exist.'})

#         # Handle customer
#         if request.user.is_authenticated:
#             customer = request.user.customer
#         else:
#             first_name = request.POST.get('first_name')
#             last_name = request.POST.get('last_name')
#             email = request.POST.get('email')
#             phone_number = request.POST.get('phone_number')
#             print("first_name", first_name, "last_name", first_name, email, phone_number)  # Keeping original debug print

#             if not first_name or not phone_number:
#                 return JsonResponse({'success': False, 'error': 'Please provide your details to proceed.'})

#             customer, created = Customer.objects.get_or_create(
#                 email=email,
#                 defaults={
#                     'first_name': first_name,
#                     'last_name': last_name,
#                     'phone_number': phone_number,
#                     'is_registered': False
#                 }
#             )

#         # Create appointment
#         Appointment.objects.create(
#             customer=customer,
#             service=service,
#             appointment_date=appointment_datetime,
#             status='pending'
#         )

#         return JsonResponse({
#             'success': True,
#             'appointment_date': appointment_datetime.strftime("%Y-%m-%d %H:%M"),
#             'service_name': service.name
#         })

#     return JsonResponse({'success': False, 'error': 'Invalid request method.'})



def book_appointment(request):
    if request.method == 'POST':
        print("Request POST Data:", request.POST)  # Keeping original debug print
        
        # Extract form data
        service_id = request.POST.get('service_id')
        date = request.POST.get('date')
        time = request.POST.get('time')

        # Validate required fields
        if not service_id or not date or not time:
            return JsonResponse({'success': False, 'error': 'Please fill out all required fields.'})

        # Parse datetime
        try:
            appointment_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            appointment_datetime = make_aware(appointment_datetime)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date or time format.'})

        # Fetch service
        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'The selected service does not exist.'})

        # Handle customer
        if request.user.is_authenticated:
            customer = request.user.customer
            is_registered = customer.is_registered
        else:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            print("first_name", first_name, "last_name", first_name, email, phone_number)  # Keeping original debug print

            if not first_name or not phone_number:
                return JsonResponse({'success': False, 'error': 'Please provide your details to proceed.'})

                        # Ensure the session exists
            if not request.session.session_key:
                request.session.create()
            session_id = request.session.session_key

            # Try to find an existing customer by email (for registered users) OR session_id (for guests)
            customer, created = Customer.objects.get_or_create(
                email=email if email else None,  # Only use email if provided
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number,
                    'session_id': session_id,  # Store session ID for guests
                    'is_registered': False
                }
            )

            # If the customer exists but has no session_id (old guest accounts), update it
            if not customer.session_id:
                customer.session_id = session_id
                customer.save()

            is_registered = customer.is_registered

        # Create appointment
        appointment = Appointment.objects.create(
            customer=customer,
            service=service,
            appointment_date=appointment_datetime,
            status='pending'
        )

        # Reward loyalty points **only for registered users**
        loyalty_points_earned = 0
        message = "Thank you for booking!"

        if is_registered:
            loyalty_points_earned = int(service.price * 0.10)  # Earn 10% of service price as points
            # customer.loyalty_points += loyalty_points_earned
            # customer.save()
        else:
            message1 = "Book as a registered user to earn and redeem loyalty points!"
            loyalty_points_earned = message1
        total_cost = service.price

        return JsonResponse({
            'success': True,
            'appointment_date': appointment_datetime.strftime("%Y-%m-%d %H:%M"),
            'service_name': service.name,
            'loyalty_points_earned': loyalty_points_earned,
            'total_cost': total_cost,
            'message': message
        })

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})