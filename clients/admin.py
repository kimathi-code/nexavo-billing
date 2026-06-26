from django.contrib import admin
from .models import (
    Client,
    NotificationLog,
    Subscription,
    Package,
    MikroTikLog,
    Payment,
    Invoice,
    MpesaTransaction,
    StkPushRequest
)


# Register your models here.


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'phone',
        'email',
        'account_number',
        'pppoe_username',
        'location',
        'created_at',
        'created_by',
        'updated_by'
    )
    search_fields = ('name', 'phone')
    list_filter = ('created_at',)

admin.site.register(Package)

admin.site.register(Subscription)

@admin.register(StkPushRequest)
class StkPushRequestAdmin(admin.ModelAdmin):

    list_display = (
        "account_reference",
        "merchant_request_id",
        "phone_number",
        "amount",
        "status",
        "response_code",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "account_reference",
        "phone_number",
        "merchant_request_id",
        "checkout_request_id",
    )

    readonly_fields = (
        "merchant_request_id",
        "checkout_request_id",
        "raw_response",
        "created_at",
        "updated_at",
    )

    fields = (
        "account_reference",
        "phone_number",
        "amount",
        "status",
        "merchant_request_id",
        "checkout_request_id",
        "response_code",
        "response_description",
        "raw_response",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

@admin.register(MikroTikLog)
class MikroTikLogAdmin(admin.ModelAdmin):

    list_display = (
        'client',
        'pppoe_username',
        'action',
        'created_at'
    )

    list_filter = (
        'action',
        'created_at'
    )

    search_fields = (
        'pppoe_username',
        'client__name'
    )

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):

    list_display = (
        'client',
        'notification_type',
        'created_at'
    )

    search_fields = (
        'client__name',
        'client__account_number'
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        'client',
        'amount',
        'transaction_code',
        'payment_method',
        'created_at'
    )

    search_fields = (
        'transaction_code',
        'client__name'
    )

    list_filter = (
        'payment_method',
        'created_at'
    )

@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):

    list_display = (
        'receipt_number',
        'account_reference',
        'phone_number',
        'amount',
        'created_at'
    )

    search_fields = (
        'receipt_number',
        'account_reference',
        'phone_number'
    )

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    list_display = (
        'invoice_number',
        'client',
        'amount',
        'amount_paid',
        'balance_due',
        'billing_period_start',
        'billing_period_end',
        'due_date',
        'status'
    )

    search_fields = (
        'invoice_number',
        'client__name'
    )

    list_filter = (
        'status',
        'due_date'
    )
