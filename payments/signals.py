from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from .views import process_upline_payment

@receiver(post_save, sender=Payment)
def process_payment_on_approval(sender, instance, **kwargs):
    if instance.status == 'approved' and not kwargs.get('created', False):
        process_upline_payment(instance)