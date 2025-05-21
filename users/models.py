from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.core.exceptions import ValidationError

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    national_id = models.CharField(max_length=50, unique=True, blank=False)
    kyc_document = models.ImageField(upload_to='kyc_documents/', blank=True, null=True)
    kyc_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    referral = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_by')
    cbe_account_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name or 'Unknown'} {self.last_name or 'Unknown'} - {self.kyc_status}"

    def clean(self):
        # Existing validation for email and phone number
        if self.email and self.phone_number:
            existing_profiles = UserProfile.objects.filter(email=self.email, phone_number=self.phone_number)
            if self.pk:
                existing_profiles = existing_profiles.exclude(pk=self.pk)
            if existing_profiles.count() >= 20:
                raise ValidationError("You cannot create more than 20 accounts with the same email and phone number.")

        # Validate CBE account number
        if self.cbe_account_number:
            if not self.cbe_account_number.isdigit():
                raise ValidationError("CBE account number must contain only digits.")
            if len(self.cbe_account_number) < 10:
                raise ValidationError("CBE account number must be at least 10 digits long.")

# Signal to auto-generate user ID on creation
def generate_user_id(sender, instance, created, **kwargs):
    if created and not instance.username:  # Only generate if no username is set
        while True:
            characters = string.ascii_letters + string.digits
            user_id = ''.join(random.choice(characters) for _ in range(7))
            if not User.objects.filter(username=user_id).exists():
                instance.username = user_id
                instance.save()
                break

from django.db.models.signals import post_save
post_save.connect(generate_user_id, sender=User)