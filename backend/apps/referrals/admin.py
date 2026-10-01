from django.contrib import admin

from .models import (
    CommissionRecord,
    Referral,
    ReferralCampaign,
    ReferralCampaignTier,
    ReferralConversion,
    ReferralProfile,
    RewardCoupon,
)


@admin.register(ReferralProfile)
class ReferralProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "code", "created_at"]
    search_fields = ["user__username", "code"]


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ["referrer", "referred_user", "status", "is_flagged", "created_at"]
    list_filter = ["status", "is_flagged"]
    search_fields = ["referrer__username", "referred_user__username"]


class ReferralCampaignTierInline(admin.TabularInline):
    model = ReferralCampaignTier
    extra = 1


@admin.register(ReferralCampaign)
class ReferralCampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "active", "is_default", "category", "created_at"]
    list_filter = ["active", "category"]
    search_fields = ["name"]
    inlines = [ReferralCampaignTierInline]


@admin.register(RewardCoupon)
class RewardCouponAdmin(admin.ModelAdmin):
    list_display = ["code", "owner", "campaign", "status", "discount_percent", "expires_at"]
    list_filter = ["status"]
    search_fields = ["code", "owner__username"]


@admin.register(ReferralConversion)
class ReferralConversionAdmin(admin.ModelAdmin):
    list_display = ["referral", "payment", "amount", "is_first_qualifying", "is_reversed", "created_at"]
    list_filter = ["is_first_qualifying", "is_reversed"]


@admin.register(CommissionRecord)
class CommissionRecordAdmin(admin.ModelAdmin):
    list_display = ["payment", "referral", "gross_amount", "commission_amount", "created_at"]
