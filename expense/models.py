# models.py
from django.db import models
from django.utils.timezone import now

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    FREQUENCY_CHOICES = [
        ('NONE', 'None'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(default=now)  # Start date for recurring expenses
    end_date = models.DateField(null=True, blank=True)  # Optional end date
    last_generated = models.DateField(null=True, blank=True)  # Tracks the last generated occurrence
    recurring_frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default='NONE'
    )
    is_paid = models.BooleanField(default=False)  # Payment status

    def __str__(self):
        return f"{self.category.name} - {self.amount} ({'Paid' if self.is_paid else 'Unpaid'})"

class Payment(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=now)

    def __str__(self):
        return f"Payment of {self.amount_paid} for {self.expense}"