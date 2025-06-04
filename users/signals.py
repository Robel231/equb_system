from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile
from equb.models import EqubMember
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=UserProfile)
def create_equb_member_on_kyc_approval(sender, instance, **kwargs):
    if instance.kyc_status == 'approved':
        # Check if EqubMember already exists to avoid duplicates
        if not EqubMember.objects.filter(user=instance.user).exists():
            max_queue = EqubMember.objects.aggregate(models.Max('queue_position'))['queue_position__max'] or 0
            EqubMember.objects.create(
                user=instance.user,
                queue_position=max_queue + 1,
                round_number=1,
                status='active',
                upline=None
            )
            logger.info(f"Created EqubMember for {instance.user.username} with queue position {max_queue + 1}")