from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile
import random
import string

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=False)
    last_name = forms.CharField(max_length=50, required=False)
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(max_length=15, required=False)
    national_id = forms.CharField(max_length=50, required=True)
    kyc_document = forms.ImageField(required=False)
    referral = forms.CharField(max_length=100, required=False)
    num_accounts = forms.IntegerField(min_value=1, required=True, initial=1)
    cbe_account_number = forms.CharField(max_length=20, required=False, help_text="Enter your Commercial Bank of Ethiopia account number (optional).")

    class Meta:
        model = User
        fields = ('password1', 'password2', 'first_name', 'last_name', 'email', 'phone_number', 'national_id', 'kyc_document', 'referral', 'num_accounts', 'cbe_account_number')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and UserProfile.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and UserProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already in use.")
        return phone_number

    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if UserProfile.objects.filter(national_id=national_id).exists():
            raise forms.ValidationError("This national ID is already in use.")
        return national_id

    def clean_cbe_account_number(self):
        cbe_account_number = self.cleaned_data.get('cbe_account_number')
        if cbe_account_number:
            if not cbe_account_number.isdigit():
                raise forms.ValidationError("CBE account number must contain only digits.")
            if len(cbe_account_number) < 10:
                raise forms.ValidationError("CBE account number must be at least 10 digits long.")
        return cbe_account_number

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            # Generate username before saving
            while True:
                characters = string.ascii_letters + string.digits
                user_id = ''.join(random.choice(characters) for _ in range(7))
                if not User.objects.filter(username=user_id).exists():
                    user.username = user_id
                    user.save()
                    break

            # Create UserProfile
            UserProfile.objects.create(
                user=user,
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                email=self.cleaned_data['email'],
                phone_number=self.cleaned_data['phone_number'],
                national_id=self.cleaned_data['national_id'],
                kyc_document=self.cleaned_data['kyc_document'],
                referral=User.objects.filter(username=self.cleaned_data['referral']).first() if self.cleaned_data['referral'] else None,
                cbe_account_number=self.cleaned_data.get('cbe_account_number')
            )
        return user