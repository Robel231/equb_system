from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'national_id', 'kyc_status', 'created_at', 'kyc_document_link', 'cbe_account_number')
    list_filter = ('kyc_status', 'created_at')
    search_fields = ('user__username', 'national_id', 'email', 'phone_number')
    actions = ['approve_kyc', 'reject_kyc']

    def full_name(self, obj):
        return f"{obj.first_name or 'Unknown'} {obj.last_name or 'Unknown'}"
    full_name.short_description = "Name"

    def kyc_document_link(self, obj):
        if obj.kyc_document:
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.kyc_document.url)
        return "No Document"
    kyc_document_link.short_description = "KYC Document"

    def approve_kyc(self, request, queryset):
        queryset.update(kyc_status='approved')
    approve_kyc.short_description = "Approve selected KYC submissions"

    def reject_kyc(self, request, queryset):
        queryset.update(kyc_status='rejected')
    reject_kyc.short_description = "Reject selected KYC submissions"

admin.site.register(UserProfile, UserProfileAdmin)