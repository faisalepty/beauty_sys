# customers/models.py
from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import User

# class Customer(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
#     first_name = models.CharField(max_length=100)
#     last_name = models.CharField(max_length=100)
#     email = models.EmailField(unique=True)
#     phone_number = models.CharField(max_length=15, blank=True, null=True)
#     loyalty_points = models.PositiveIntegerField(default=0)  # Total loyalty points balance
#     created_at = models.DateTimeField(auto_now_add=True)
#     is_registered = models.BooleanField(default=False, blank=True, null=True)  # Flag to track registration status

#     def __str__(self):
#         return f"{self.first_name} {self.last_name}"

#     def add_loyalty_points(self, points):
#         """Add loyalty points to the customer's balance."""
#         self.loyalty_points += points
#         self.save()

#     def redeem_loyalty_points(self, points):
#         """Redeem loyalty points for a discount."""
#         if self.loyalty_points >= points:
#             self.loyalty_points -= points
#             self.save()
#             return True
#         return False



class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=40, unique=True, null=True, blank=True)  # Track anon users
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    loyalty_points = models.PositiveIntegerField(default=0)  # Total loyalty points balance
    created_at = models.DateTimeField(auto_now_add=True)
    is_registered = models.BooleanField(default=False, blank=True, null=True)  # Flag to track registration status

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def add_loyalty_points(self, amount_spent):
        """Earn 10% of the amount spent as loyalty points."""
        points = int(amount_spent * 0.10)  # 10% of the price
        self.loyalty_points += points
        self.save()

    def max_redeemable_points(self, service_price):
        """Calculate the maximum points the customer can use for a given service."""
        return min(self.loyalty_points, int(service_price * 0.25))  # 25% of the price

    def redeem_loyalty_points(self, service_price):
        """Redeem points up to 25% of the service price."""
        max_redeem = self.max_redeemable_points(service_price)
        
        if max_redeem > 0:
            self.loyalty_points -= max_redeem
            self.save()
            return max_redeem  # Amount discounted
        
        return 0  # No discount if insufficient points
