# Generated by Django 5.1.6 on 2025-04-03 07:57

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.TextField(blank=True, null=True)),
                ('start_date', models.DateField(default=django.utils.timezone.now)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('last_generated', models.DateField(blank=True, null=True)),
                ('recurring_frequency', models.CharField(choices=[('NONE', 'None'), ('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly'), ('YEARLY', 'Yearly')], default='NONE', max_length=10)),
                ('is_paid', models.BooleanField(default=False)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expenses', to='expense.category')),
            ],
        ),
        # migrations.CreateModel(
        #     name='Payment',
        #     fields=[
        #         ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        #         ('amount_paid', models.DecimalField(decimal_places=2, max_digits=10)),
        #         ('payment_date', models.DateField(default=django.utils.timezone.now)),
        #         ('expense', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='expense.expense')),
        #     ],
        # ),
    ]
