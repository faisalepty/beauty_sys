# staff/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # List staff members (HTML or JSON response for AJAX)
    path('list/', views.staff_list, name='staff_list'),

    # Create or update a staff member (AJAX only)
    path('create-update/', views.staff_create_update, name='staff_create_update'),

    # Delete a staff member (AJAX only)
    path('delete/', views.staff_delete, name='staff_delete'),

    # Fetch details of a specific staff member (AJAX only)
    path('<int:pk>/', views.staff_detail, name='staff_detail'),


    path('notifications/', views.staff_notifications, name='staff_notifications'),
      path('mark-confirmed/<int:appointment_id>/', views.mark_confirmed, name='mark_confirmed'),
    path('get-appointment-details/<int:appointment_id>/', views.get_appointment_details, name='get_appointment_details'),


]