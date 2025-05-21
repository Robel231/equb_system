from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import models
from .forms import CustomUserCreationForm
from .models import UserProfile
from django.contrib.auth.models import User
from equb.models import EqubMember
import random
import string
from django.utils import timezone

def register(request):
    try:
        print(f"Request method: {request.method}")
        if request.method == 'POST':
            form = CustomUserCreationForm(request.POST, request.FILES)
            if form.is_valid():
                user_ids = []
                num_accounts = int(form.cleaned_data['num_accounts'])
                print(f"Number of accounts requested: {num_accounts}")
                referral = User.objects.filter(username=form.cleaned_data['referral']).first() if form.cleaned_data['referral'] else None
                base_national_id = form.cleaned_data['national_id']
                kyc_document = form.cleaned_data['kyc_document']
                cbe_account_number = form.cleaned_data.get('cbe_account_number')

                upline = None
                if referral:
                    upline = EqubMember.objects.filter(user=referral, status='active').first()
                    if not upline:
                        print(f"Warning: Referral {referral.username} does not have an active EqubMember record.")

                for i in range(num_accounts):
                    print(f"Creating account {i+1} of {num_accounts}")
                    while True:
                        characters = string.ascii_letters + string.digits
                        user_id = ''.join(random.choice(characters) for _ in range(7))
                        if not User.objects.filter(username=user_id).exists():
                            break
                    user = User.objects.create_user(username=user_id, password=form.cleaned_data['password1'])
                    unique_national_id = f"{base_national_id}-{i}" if i > 0 else base_national_id
                    while UserProfile.objects.filter(national_id=unique_national_id).exists():
                        unique_national_id = f"{base_national_id}-{i}-{random.randint(100, 999)}"
                    profile = UserProfile.objects.create(
                        user=user,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        email=form.cleaned_data['email'],
                        phone_number=form.cleaned_data['phone_number'],
                        national_id=unique_national_id,
                        kyc_document=kyc_document,
                        referral=referral,
                        kyc_status='pending',
                        cbe_account_number=cbe_account_number
                    )
                    max_queue = EqubMember.objects.aggregate(models.Max('queue_position'))['queue_position__max'] or 0
                    equb_member = EqubMember.objects.create(
                        user=user,
                        queue_position=max_queue + 1,
                        round_number=1,
                        status='active',
                        upline=upline
                    )
                    user_ids.append(user_id)

                print(f"SMS Sent: Your User IDs are: {', '.join(user_ids)}. Use these to log in.")
                return render(request, 'users/registration_success.html', {'user_ids': user_ids})
            else:
                print("Form errors:", form.errors)
        else:
            form = CustomUserCreationForm()
            print("Rendering registration form")
        return render(request, 'users/register.html', {'form': form})
    except Exception as e:
        print(f"Error in register view: {str(e)}")
        return render(request, 'users/register.html', {'form': form, 'error': str(e)})

@login_required
def upload_kyc(request):
    if request.method == 'POST':
        national_id = request.POST.get('national_id')
        if request.FILES.get('kyc_file'):
            profile = request.user.userprofile
            if UserProfile.objects.filter(national_id=national_id).exclude(id=profile.id).exists():
                return render(request, 'users/upload_kyc.html', {'error': 'National ID already exists.'})
            profile.national_id = national_id
            profile.kyc_document = request.FILES['kyc_file']
            profile.save()
            return redirect('dashboard')
    return render(request, 'users/upload_kyc.html')