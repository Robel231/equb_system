from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Payment, Transaction
from users.models import UserProfile
from equb.models import EqubMember
from django.db import transaction

@login_required
def upload_payment(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_proof = request.FILES.get('payment_proof')
        if amount and payment_proof:
            try:
                amount = float(amount)
                if amount <= 0:
                    raise ValueError("Amount must be greater than 0")
                payment = Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    payment_proof=payment_proof,
                    status='pending'
                )
                return redirect('dashboard')
            except ValueError:
                return render(request, 'payments/upload_payment.html', {'error': 'Invalid amount'})
        return render(request, 'payments/upload_payment.html', {'error': 'Please provide amount and payment proof'})
    return render(request, 'payments/upload_payment.html')

def process_upline_payment(payment):
    """Distribute 50% of the payment to the upline and 50% to the pool."""
    print(f"Processing payment for user: {payment.user.username}, amount: {payment.amount}")
    user_profile = payment.user.userprofile
    upline = user_profile.referral  # The referrer (upline User)
    total_amount = payment.amount

    with transaction.atomic():
        # 50% to upline (if exists and their active EqubMember is not completed)
        upline_amount = 0
        if upline:
            print(f"Upline found: {upline.username}")
            upline_member = EqubMember.objects.filter(user=upline, status='active').first()
            if upline_member:
                print(f"Upline member active, distributing {total_amount * 0.5} ETB")
                upline_amount = total_amount * 0.5
                Transaction.objects.create(
                    payment=payment,
                    recipient=upline,
                    amount=upline_amount,
                    transaction_type='upline'
                )
            else:
                print("Upline member not active or not found")
        else:
            print("No upline found")

        # 50% to the pool
        pool_amount = total_amount - upline_amount
        print(f"Distributing {pool_amount} ETB to pool")
        Transaction.objects.create(
            payment=payment,
            recipient=payment.user,  # Placeholder for pool
            amount=pool_amount,
            transaction_type='pool'
        )