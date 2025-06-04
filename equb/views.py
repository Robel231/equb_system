from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import EqubMember
from payments.models import Payment, Transaction
from users.models import UserProfile
from django.contrib.auth.models import User
import decimal
import logging
from django.db.models import Sum, Max

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'equb/home.html')

@login_required
def dashboard(request):
    member = EqubMember.objects.filter(user=request.user, status__in=['active', 'completed']).first()
    payments = Payment.objects.filter(user=request.user, status='pending')
    kyc_status = request.user.userprofile.kyc_status

    # Aggregated payment history
    received_payments = Payment.objects.filter(transactions__recipient=request.user, status='approved')\
        .values('user__username', 'user__id')\
        .annotate(total_amount=Sum('amount'), latest_date=Max('created_at'))\
        .order_by('-latest_date')
    made_payments = Payment.objects.filter(user=request.user, status='approved')\
        .values('transactions__recipient__username', 'transactions__recipient__id')\
        .annotate(total_amount=Sum('amount'), latest_date=Max('created_at'))\
        .order_by('-latest_date')

    payment_history = []
    for pr in received_payments:
        payment = Payment.objects.filter(user__username=pr['user__username'], transactions__recipient=request.user, status='approved').order_by('-created_at').first()
        payment_history.append({
            'date': pr['latest_date'],
            'type': 'downline_payment',
            'amount': pr['total_amount'],
            'direction': 'Received',
            'other_party': f"From: {pr['user__username']} (ID: {pr['user__id']})",
            'proof_url': payment.payment_proof.url if payment and payment.payment_proof else None
        })
    for pm in made_payments:
        payment = Payment.objects.filter(user=request.user, transactions__recipient__username=pm['transactions__recipient__username'], status='approved').order_by('-created_at').first()
        payment_history.append({
            'date': pm['latest_date'],
            'type': 'upline_payment',
            'amount': pm['total_amount'],
            'direction': 'Paid',
            'other_party': f"To: {pm['transactions__recipient__username']} (ID: {pm['transactions__recipient__id']})",
            'proof_url': payment.payment_proof.url if payment and payment.payment_proof else None
        })
    payment_history.sort(key=lambda x: x['date'], reverse=True)

    # Team list
    team_list = EqubMember.objects.filter(upline__user=request.user).select_related('user')

    # Assign members based on queue position
    if member and member.status == 'active':
        start_position = (member.queue_position - 1) * 4 + 2
        expected_positions = list(range(start_position, start_position + 4))
        current_downlines = EqubMember.objects.filter(upline=member, status='active')
        
        if current_downlines.count() < 4:
            available_members = EqubMember.objects.filter(status='active', upline__isnull=True).order_by('queue_position')
            for pos in expected_positions[current_downlines.count():]:
                next_member = next((m for m in available_members if m.queue_position >= pos), None)
                if next_member:
                    logger.info(f"Assigning {next_member.user.username} (Queue {next_member.queue_position}) to {member.user.username} (Queue {member.queue_position})")
                    next_member.upline = member
                    next_member.save()
                else:
                    logger.warning(f"No available member found starting from queue position {pos} for {member.user.username}")

    # Upline payment details (for queue > 1)
    upline_member = None
    upline_amount = 0
    upline_account_number = "Not applicable"
    upline_payment_due = False
    payment_status_message = None
    if member and member.upline and member.queue_position > 1:
        initial_payment = decimal.Decimal('3000')
        full_payment_per_round = decimal.Decimal('12000')  # 4 × 3000 ETB
        half_payment = decimal.Decimal('6000')  # 50% of 12000 ETB
        downlines = EqubMember.objects.filter(upline=member, status='active')
        # Get users of downlines
        downline_users = downlines.values_list('user', flat=True)
        # Find approved payments from downlines to this member
        approved_payments = Payment.objects.filter(
            user__in=downline_users,
            status='approved',
            transactions__recipient=member.user
        ).distinct()
        paid_downlines = downlines.filter(user__in=approved_payments.values('user')).distinct()

        if member.total_paid_to_upline < initial_payment:
            upline_amount = initial_payment - member.total_paid_to_upline
            payment_status_message = f"You must pay the remaining initial amount of {upline_amount:.2f} ETB to your upline {member.upline.user.username} to start participating."
            upline_payment_due = True
        elif paid_downlines.count() == 2 and member.total_paid_to_upline < initial_payment + half_payment:
            upline_amount = half_payment
            payment_status_message = f"You've received 6000 ETB from 2 downlines. Please pay {upline_amount:.2f} ETB to your upline {member.upline.user.username}."
            upline_payment_due = True
        elif paid_downlines.count() == 4 and member.total_paid_to_upline < initial_payment + full_payment_per_round:
            remaining_amount = full_payment_per_round - (member.total_paid_to_upline - initial_payment)
            if remaining_amount > 0:
                upline_amount = remaining_amount
                payment_status_message = f"You've received 12000 ETB from 4 downlines. Please pay the remaining {upline_amount:.2f} ETB to your upline {member.upline.user.username}."
                upline_payment_due = True
        if member.upline.user.userprofile.cbe_account_number:
            upline_account_number = member.upline.user.userprofile.cbe_account_number
        else:
            upline_account_number = "Not provided"
        upline_member = member.upline

    return render(request, 'equb/dashboard.html', {
        'member': member,
        'payments': payments,
        'kyc_status': kyc_status,
        'payment_history': payment_history,
        'team_list': team_list,
        'upline_member': upline_member,
        'upline_amount': upline_amount,
        'upline_account_number': upline_account_number,
        'upline_payment_due': upline_payment_due,
        'payment_status_message': payment_status_message,
        'error': request.session.pop('error', None) if 'error' in request.session else None
    })

@login_required
def refer_member(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')

        if username and email:
            try:
                if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                    return render(request, 'equb/referral.html', {'error': 'Username or email already exists.'})

                new_user = User.objects.create_user(username=username, email=email, password='defaultpassword123')
                new_user.save()

                UserProfile.objects.create(user=new_user, kyc_status='pending')

                max_queue = EqubMember.objects.aggregate(models.Max('queue_position'))['queue_position__max'] or 0
                new_member = EqubMember.objects.create(
                    user=new_user,
                    queue_position=max_queue + 1,
                    round_number=1,
                    status='active',
                    upline=None
                )

                referrer_member = EqubMember.objects.filter(user=request.user, status__in=['active', 'completed']).first()
                if referrer_member:
                    commission = decimal.Decimal('500')
                    referrer_member.commission_earned += commission
                    referrer_member.save()
                    
                    payment = Payment.objects.create(
                        user=request.user,
                        amount=commission,
                        status='approved',
                        payment_proof=None
                    )
                    Transaction.objects.create(
                        payment=payment,
                        recipient=request.user,
                        amount=commission,
                        transaction_type='commission'
                    )

                return render(request, 'equb/referral.html', {'success': 'Referral successful! Commission credited.'})
            except Exception as e:
                return render(request, 'equb/referral.html', {'error': str(e)})
        else:
            return render(request, 'equb/referral.html', {'error': 'Please provide both username and email.'})
    return render(request, 'equb/referral.html')