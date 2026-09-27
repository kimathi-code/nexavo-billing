from django.contrib import admin

from .models import (
    HotspotLocation,
    HotspotPlan,
    HotspotVoucher,
    HotspotPurchase,
    HotspotSession,
)


@admin.register(HotspotLocation)
class HotspotLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("name", "address")


@admin.register(HotspotPlan)
class HotspotPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "duration_minutes",
        "data_limit_mb",
        "download_speed_kbps",
        "upload_speed_kbps",
        "active",
    )
    list_filter = ("active",)
    search_fields = ("name",)


@admin.register(HotspotVoucher)
class HotspotVoucherAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "plan",
        "status",
        "activated_at",
        "expires_at",
        "bound_mac",
        "data_used_mb",
    )
    list_filter = ("status", "plan")
    search_fields = ("code", "bound_mac")


@admin.register(HotspotPurchase)
class HotspotPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "voucher",
        "amount",
        "payment_method",
        "status",
        "transaction_reference",
        "created_at",
        "paid_at",
    )
    list_filter = ("status", "payment_method")
    search_fields = (
        "transaction_reference",
        "phone_number",
    )


@admin.register(HotspotSession)
class HotspotSessionAdmin(admin.ModelAdmin):
    list_display = (
        "voucher",
        "location",
        "mac_address",
        "ip_address",
        "started_at",
        "ended_at",
        "bytes_in",
        "bytes_out",
    )
    list_filter = ("location",)
    search_fields = (
        "mac_address",
        "ip_address",
        "username",
        "voucher__code",
    )
