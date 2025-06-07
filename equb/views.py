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

    # Upline and service fee payment details (for queue > 1)
    upline_member = None
    upline_amount = 0
    upline_account_number = "Not applicable"
    upline_payment_due = False
    payment_status_message = None
    referral_obligation = False
    service_fee_due = False
    service_fee_message = None
    service_fee_amount = decimal.Decimal('0')

    if member and member.upline and member.queue_position > 1:
        initial_payment = decimal.Decimal('3000')
        payment_amount = decimal.Decimal(str(member.get_payment_amount()))
        full_payment_per_round = payment_amount * 4
        half_payment_threshold = member.get_half_payment_threshold()
        service_fee = full_payment_per_round * decimal.Decimal('0.1')
        net_to_member = {
            1: decimal.Decimal('5400'),
            2: decimal.Decimal('10800'),
            3: decimal.Decimal('21600'),
            4: decimal.Decimal('43200'),
            5: decimal.Decimal('76800'),
            6: decimal.Decimal('345600')
        }

        downlines = EqubMember.objects.filter(upline=member, status='active')
        downline_users = downlines.values_list('user', flat=True)
        approved_payments = Payment.objects.filter(
            user__in=downline_users,
            status='approved',
            transactions__recipient=member.user
        ).distinct()
        paid_downlines = downlines.filter(user__in=approved_payments.values('user')).distinct()
        total_received = sum(p.amount for p in approved_payments)

        if member.total_paid_to_upline < initial_payment:
            upline_amount = initial_payment - member.total_paid_to_upline
            payment_status_message = f"You must pay the remaining initial amount of {upline_amount:.2f} ETB to your upline {member.upline.user.username} to start participating."
            upline_payment_due = True
        elif member.round_number <= 5:  # Apply payment logic for rounds 1-5
            if paid_downlines.count() == 2 and total_received >= full_payment_per_round * decimal.Decimal('0.5') and member.total_paid_to_upline < initial_payment + (half_payment_threshold * decimal.Decimal('0.5')):
                upline_amount = half_payment_threshold * decimal.Decimal('0.5')
                payment_status_message = f"You've received {total_received:.2f} ETB from 2 downlines. Please pay {upline_amount:.2f} ETB to your upline {member.upline.user.username}."
                upline_payment_due = True
            elif paid_downlines.count() == 4 and total_received >= full_payment_per_round and member.total_paid_to_upline < initial_payment + half_payment_threshold:
                remaining_amount = half_payment_threshold - (member.total_paid_to_upline - initial_payment)
                if remaining_amount > 0:
                    upline_amount = remaining_amount
                    payment_status_message = f"You've received {total_received:.2f} ETB from 4 downlines. Please pay the remaining {upline_amount:.2f} ETB to your upline {member.upline.user.username}."
                    upline_payment_due = True
                # Check if service fee is due after full payment and upline payment
                total_service_fee_paid = member.total_service_fee_paid
                if paid_downlines.count() == 4 and total_received >= full_payment_per_round and total_service_fee_paid < service_fee:
                    service_fee_due = True
                    referrer_fee = decimal.Decimal('0')
                    company_fee = service_fee
                    if member.upline:
                        referrer_fee = service_fee * decimal.Decimal('0.5')  # 5% to referrer
                        company_fee = service_fee * decimal.Decimal('0.5')  # 5% to company
                        # Credit referrer commission if not already paid
                        if not Payment.objects.filter(user=member.upline.user, amount=referrer_fee, status='approved', transaction__type='referral_commission').exists():
                            member.upline.commission_earned += referrer_fee
                            member.upline.save()
                            Payment.objects.create(
                                user=member.upline.user,
                                amount=referrer_fee,
                                status='approved',
                                payment_proof=None
                            )
                            Transaction.objects.create(
                                payment=Payment.objects.latest('id'),
                                recipient=member.upline.user,
                                amount=referrer_fee,
                                transaction_type='referral_commission'
                            )
                    service_fee_message = f"Service fee is due after receiving full payment. Please pay {company_fee:.2f} ETB to the company and {referrer_fee:.2f} ETB to your referrer (if applicable) for a total of {service_fee:.2f} ETB."
        elif member.round_number == 6:  # 6th round obligation
            referral_obligation = True
            service_fee = full_payment_per_round * decimal.Decimal('0.1')
            total_service_fee_paid = member.total_service_fee_paid
            if total_received >= full_payment_per_round and total_service_fee_paid < service_fee:
                service_fee_due = True
                referrer_fee = decimal.Decimal('0')
                company_fee = service_fee
                if member.upline:
                    company_fee = service_fee * decimal.Decimal('0.5')
                    referrer_fee = service_fee * decimal.Decimal('0.5')
                    if not Payment.objects.filter(user=member.upline.user, amount=referrer_fee, status='approved', transaction__type='referral_commission').exists():
                        member.upline.commission_earned += referrer_fee
                        member.upline.save()
                        Payment.objects.create(
                            user=member.upline.user,
                            amount=referrer_fee,
                            status='approved',
                            payment_proof=None
                        )
                        Transaction.objects.create(
                            payment=Payment.objects.latest('id'),
                            recipient=member.upline.user,
                            amount=referrer_fee,
                            transaction_type='referral_commission'
                        )
                service_fee_message = f"You have reached the 6th round. You received {total_received:.2f} ETB. Service fee is due: {company_fee:.2f} ETB to the company and {referrer_fee:.2f} ETB to your referrer (if applicable) for a total of {service_fee:.2f} ETB. You are also obligated to create 5 new accounts."
            else:
                payment_status_message = f"You have reached the 6th round. You received {total_received:.2f} ETB (service fee: {company_fee:.2f} ETB, referrer fee: {referrer_fee:.2f} ETB if applicable). You are obligated to create 5 new accounts."

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
        'referral_obligation': referral_obligation,
        'service_fee_due': service_fee_due,
        'service_fee_message': service_fee_message,
        'service_fee_amount': service_fee_amount,
        'error': request.session.pop('error', None) if 'error' in request.session else None
    })

@login_required
def refer_member(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        name = request.POST.get('name')

        if username and email and name:
            try:
                if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                    return render(request, 'equb/referral.html', {'error': 'Username or email already exists.'})

                new_user = User.objects.create_user(username=username, email=email, password='defaultpassword123')
                new_user.save()

                UserProfile.objects.create(user=new_user, kyc_status='pending', cbe_account_number=None)  # Adjusted to match existing fields

                max_queue = EqubMember.objects.aggregate(Max('queue_position'))['queue_position__max'] or 0
                new_member = EqubMember.objects.create(
                    user=new_user,
                    queue_position=max_queue + 1,
                    round_number=1,
                    status='active',
                    upline=None,
                    total_service_fee_paid=decimal.Decimal('0')
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
                    new_member.upline = referrer_member
                    new_member.save()

                return render(request, 'equb/referral.html', {'success': 'Referral successful! Commission credited.'})
            except Exception as e:
                return render(request, 'equb/referral.html', {'error': str(e)})
        else:
            return render(request, 'equb/referral.html', {'error': 'Please provide username, email, and name.'})
    return render(request, 'equb/referral.html')