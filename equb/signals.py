from django.db.models.signals import post_save
from django.dispatch import receiver
from payments.models import Payment, Transaction
from .models import EqubMember
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Payment)
def update_member_totals(sender, instance, **kwargs):
    if instance.status == 'approved' and kwargs.get('created', False):
        # Update recipient's total_received
        try:
            transaction = Transaction.objects.filter(payment=instance).first()
            if transaction:
                recipient_member = EqubMember.objects.filter(user=transaction.recipient, status='active').first()
                if recipient_member:
                    with transaction.atomic():
                        previous_total = recipient_member.total_received
                        recipient_member.total_received += instance.amount
                        recipient_member.save()
                        logger.info(f"Updated total_received for {transaction.recipient.username} from {previous_total} to {recipient_member.total_received} ETB for payment {instance.id}")
        except Exception as e:
            logger.error(f"Error updating total_received for payment {instance.id}: {str(e)}")

@receiver(post_save, sender=Transaction)
def check_round_completion(sender, instance, **kwargs):
    # Only process on save (not creation) to handle updates
    if not kwargs.get('created', False):
        payment = instance.payment
        member = EqubMember.objects.filter(user=payment.user, status='active').first()
        if member:
            full_payment_amount = member.get_payment_amount() * 4  # Total expected from 4 downlines
            logger.debug(f"Checking round completion for {member.user.username}: total_received={member.total_received}, full_payment_amount={full_payment_amount}")
            if member.total_received >= full_payment_amount and member.round_number < 6:
                member.round_number += 1
                member.total_received = 0
                member.total_paid_to_upline = 0
                member.save()
                logger.info(f"{member.user.username} advanced to round {member.round_number} after receiving {member.total_received} ETB")