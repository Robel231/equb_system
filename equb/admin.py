from django.contrib import admin
from django.utils.html import format_html
from .models import EqubMember

@admin.register(EqubMember)
class EqubMemberAdmin(admin.ModelAdmin):
    list_display = ('queue_position', 'name', 'user_id', 'phone_number', 'email', 'kyc_document_link', 'downlines')
    list_filter = ('status', 'round_number')
    search_fields = ('user__username', 'user__email')
    ordering = ('queue_position',)

    def name(self, obj):
        return obj.user.username
    name.short_description = "Name"

    def user_id(self, obj):
        return obj.user.id
    user_id.short_description = "User ID"

    def phone_number(self, obj):
        return obj.user.userprofile.phone_number if hasattr(obj.user, 'userprofile') and obj.user.userprofile.phone_number else "Not provided"
    phone_number.short_description = "Phone Number"

    def email(self, obj):
        return obj.user.email
    email.short_description = "Email"

    def kyc_document_link(self, obj):
        if hasattr(obj.user, 'userprofile') and obj.user.userprofile.kyc_document:
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.user.userprofile.kyc_document.url)
        return "No Document"
    kyc_document_link.short_description = "KYC Document"

    def downlines(self, obj):
        downlines = EqubMember.objects.filter(upline=obj, status='active')
        if downlines.exists():
            return ", ".join([downline.user.username for downline in downlines])
        return "No downlines"
    downlines.short_description = "Downlines"