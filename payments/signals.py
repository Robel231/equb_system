from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment

@receiver(post_save, sender=Payment)
def process_payment_on_approval(sender, instance, **kwargs):
    if instance.status == 'approved' and not hasattr(instance, 'processed'):
        from .views import process_upline_payment
        process_upline_payment(instance)
        instance.processed = True  # Prevent reprocessing
        instance.save()