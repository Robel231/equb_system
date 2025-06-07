from django.db import models
from django.contrib.auth.models import User
import decimal

class EqubMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    queue_position = models.PositiveIntegerField()
    round_number = models.PositiveSmallIntegerField(default=1)
    upline = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('completed', 'Completed'), ('deleted', 'Deleted')], default='active')
    total_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid_to_upline = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_service_fee_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # New field

    def get_payment_amount(self):
        amounts = {1: 3000, 2: 6000, 3: 12000, 4: 24000, 5: 48000, 6: 96000}
        return amounts.get(self.round_number, 0)

    def get_half_payment_threshold(self):
        payment_amount = decimal.Decimal(str(self.get_payment_amount()))
        return payment_amount * 4 * decimal.Decimal('0.5')

    def __str__(self):
        return f"Queue {self.queue_position} - {self.user.username}"