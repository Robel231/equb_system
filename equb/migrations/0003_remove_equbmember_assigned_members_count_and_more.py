# Generated by Django 4.2.20 on 2025-05-22 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equb', '0002_remove_equbmember_created_at_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='equbmember',
            name='assigned_members_count',
        ),
        migrations.AddField(
            model_name='equbmember',
            name='commission_earned',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
    ]
