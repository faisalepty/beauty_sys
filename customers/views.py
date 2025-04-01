from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import Customer
from appointments.models import Appointment
from billing.models import Billing

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return JsonResponse({'success': True, 'message': 'Login successful!'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid credentials. Please try again.'})

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')

        # Check if username or email exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username is already taken.'})
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email is already registered.'})

        # Create User
        user = User.objects.create_user(
            username=username,  # Fixed from original where it used first_name
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Create Customer
        customer = Customer.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            loyalty_points=0
        )

        # Log user in
        auth_login(request, user)

        return JsonResponse({'success': True, 'message': 'Registration successful!'})

@login_required
def user_logout(request):
    logout(request)
    return redirect('home')


def customer_dashboard(request):
    """Retrieve customer dashboard data using user or session_id."""
    
    customer = None
    if request.user.is_authenticated:
        # Logged-in user: Fetch customer via User
        customer = get_object_or_404(Customer, user=request.user)
    else:
        # Guest user: Fetch customer via session_id
        session_id = request.session.session_key
        if not session_id:
            request.session.create()  # Create session if missing
            session_id = request.session.session_key

        customer = Customer.objects.filter(session_id=session_id).first()

        # If no customer exists for this session, show an empty dashboard
        if not customer:
            return render(request, 'customers/dashboard.html', {
                'customer': None,
                'appointments': [],
                'loyalty_points': 0,
                'payments': [],
                'is_authenticated': False
            })

    # Fetch customer data
    appointments = Appointment.objects.filter(customer=customer).order_by('-appointment_date')
    loyalty_points = customer.loyalty_points if request.user.is_authenticated else None  # Guests don't earn points
    payments = Billing.objects.filter(appointment__customer=customer).order_by('-created_at')

    return render(request, 'customers/dashboard.html', {
        'customer': customer,
        'appointments': appointments,
        'loyalty_points': loyalty_points,
        'payments': payments,
        'is_authenticated': request.user.is_authenticated  # Pass auth status to template
    })

def register_prompt(request):
    return render(request, 'customers/register_prompt.html')