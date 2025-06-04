from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Payment, Transaction
from users.models import UserProfile
from equb.models import EqubMember
from django.db import transaction
import logging
import decimal

logger = logging.getLogger(__name__)

@login_required
def pay_upline(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_proof = request.FILES.get('payment_proof')

        if amount and payment_proof:
            try:
                amount = decimal.Decimal(amount)
                if amount <= 0:
                    raise ValueError("Amount must be greater than 0")
                member = EqubMember.objects.filter(user=request.user, status='active').first()
                if not member or not member.upline:
                    raise ValueError("No upline found")

                payment = Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    payment_proof=payment_proof,
                    status='pending'
                )
                logger.info(f"Upline payment created: ID {payment.id} for user {request.user.username} to upline {member.upline.user.username}")

                with transaction.atomic():
                    Transaction.objects.create(
                        payment=payment,
                        recipient=member.upline.user,
                        amount=amount,
                        transaction_type='upline_payment'
                    )
                    member.total_paid_to_upline += amount
                    member.save()

                return redirect('equb:dashboard')
            except (ValueError, EqubMember.DoesNotExist) as e:
                logger.error(f"Error recording upline payment: {str(e)}")
                return redirect('equb:dashboard', error=f"Error recording upline payment: {str(e)}")
        else:
            logger.warning("Missing required fields for upline payment")
            return redirect('equb:dashboard', error="Please provide all required fields")
    return redirect('equb:dashboard')

def process_upline_payment(payment):
    """
    Process an approved payment by updating the relevant EqubMember fields.
    This function is called via signals when a payment is approved.
    """
    try:
        if payment.status == 'approved':
            member = EqubMember.objects.filter(user=payment.user, status='active').first()
            if member and member.upline:
                with transaction.atomic():
                    Transaction.objects.create(
                        payment=payment,
                        recipient=member.upline.user,
                        amount=payment.amount,
                        transaction_type='upline_payment'
                    )
                    member.upline.total_received += payment.amount
                    member.total_paid_to_upline += payment.amount  # Update payer's total_paid_to_upline
                    member.upline.save()
                    member.save()
                logger.info(f"Processed payment ID {payment.id} for {payment.user.username} to upline {member.upline.user.username}")
    except Exception as e:
        logger.error(f"Error processing upline payment {payment.id}: {str(e)}")