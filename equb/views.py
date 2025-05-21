from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import EqubMember
from payments.models import Payment, Transaction
from users.models import UserProfile

def home(request):
    return render(request, 'equb/home.html')

@login_required
def dashboard(request):
    member = EqubMember.objects.filter(user=request.user).first()
    payments = Payment.objects.filter(user=request.user, status='pending')
    kyc_status = request.user.userprofile.kyc_status

    # Payment history: Transactions where the user is the recipient, with related Payment data
    payment_history = Transaction.objects.filter(recipient=request.user).select_related('payment').order_by('-created_at')

    # Team list: Members referred by this user
    team_list = EqubMember.objects.filter(upline__user=request.user).select_related('user')

    return render(request, 'equb/dashboard.html', {
        'member': member,
        'payments': payments,
        'kyc_status': kyc_status,
        'payment_history': payment_history,
        'team_list': team_list,
        'error': request.session.pop('error', None) if 'error' in request.session else None
    })

@login_required
def complete_round(request):
    member = EqubMember.objects.filter(user=request.user).first()
    if member:
        if member.round_number == 6 and member.status == 'active':
            member.status = 'completed'
            member.save()
            referred_members = EqubMember.objects.filter(upline=member).count()
            if referred_members >= 5:
                new_member = EqubMember.objects.create(
                    user=request.user,
                    queue_position=1,
                    round_number=1,
                    upline=member.upline,
                    status='active'
                )
                for downline in EqubMember.objects.filter(upline=member)[:5]:
                    if not EqubMember.objects.filter(user=downline.user, status='active').exclude(id=downline.id).exists():
                        EqubMember.objects.create(
                            user=downline.user,
                            queue_position=downline.queue_position,
                            round_number=1,
                            upline=downline.upline,
                            status='active'
                        )
            else:
                request.session['error'] = 'You must refer at least 5 users to start a new cycle.'
        elif member.round_number < 6 and member.status == 'active':
            member.round_number += 1
            member.save()
    return redirect('dashboard')