# Generated by Django 4.2.11 on 2025-06-07 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equb', '0005_remove_equbmember_initial_payment_made_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='equbmember',
            name='total_service_fee_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
