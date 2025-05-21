from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, Transaction
from .views import process_upline_payment

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('recipient', 'amount', 'transaction_type', 'created_at')
    can_delete = False

@admin.action(description="Process Upline Payment")
def process_payment_action(modeladmin, request, queryset):
    for payment in queryset:
        if payment.status == 'approved' and not hasattr(payment, 'processed'):
            process_upline_payment(payment)
            payment.processed = True
            payment.save()

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at', 'payment_proof_link')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    actions = ['approve_payments', 'reject_payments', process_payment_action]  # Combined actions
    inlines = [TransactionInline]

    def payment_proof_link(self, obj):
        if obj.payment_proof:
            return format_html('<a href="{}" target="_blank">View Proof</a>', obj.payment_proof.url)
        return "No Proof"
    payment_proof_link.short_description = "Payment Proof"

    def approve_payments(self, request, queryset):
        for payment in queryset.filter(status='pending'):
            payment.status = 'approved'
            payment.save()
            process_upline_payment(payment)  # Distribute payment
        self.message_user(request, "Selected payments have been approved and processed.")
    approve_payments.short_description = "Approve selected payments"

    def reject_payments(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, "Selected payments have been rejected.")
    reject_payments.short_description = "Reject selected payments"

admin.site.register(Transaction)  # Keep Transaction registration separate