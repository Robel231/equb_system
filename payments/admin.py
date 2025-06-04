from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, Transaction
from equb.models import EqubMember
from django.db import transaction

@admin.action(description="Record Payment from Assigned Member")
def record_assigned_payment(modeladmin, request, queryset):
    for payment in queryset:
        if payment.status == 'pending' and payment.user.userprofile.kyc_status == 'approved':
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
                    member.upline.save()
                    payment.status = 'approved'
                    payment.save()

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payer_name', 'payer_id', 'recipient_name', 'recipient_id', 'amount', 'status', 'created_at', 'payment_proof_link')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'transactions__recipient__username')
    actions = ['approve_payments', 'reject_payments', record_assigned_payment]

    def payer_name(self, obj):
        return obj.user.username
    payer_name.short_description = "Payer Name"

    def payer_id(self, obj):
        return obj.user.id
    payer_id.short_description = "Payer ID"

    def recipient_name(self, obj):
        transaction = obj.transactions.first()
        return transaction.recipient.username if transaction else "N/A"
    recipient_name.short_description = "Recipient Name"

    def recipient_id(self, obj):
        transaction = obj.transactions.first()
        return transaction.recipient.id if transaction else "N/A"
    recipient_id.short_description = "Recipient ID"

    def payment_proof_link(self, obj):
        if obj.payment_proof:
            return format_html('<a href="{}" target="_blank">View Proof</a>', obj.payment_proof.url)
        return "No Proof"
    payment_proof_link.short_description = "Payment Proof"

    def approve_payments(self, request, queryset):
        for payment in queryset.filter(status='pending'):
            payment.status = 'approved'
            payment.save()
        self.message_user(request, "Selected payments have been approved.")
    approve_payments.short_description = "Approve selected payments"

    def reject_payments(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, "Selected payments have been rejected.")
    reject_payments.short_description = "Reject selected payments"