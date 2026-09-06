from django.db import models
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings

# Client model

class Client(models.Model):

    name = models.CharField(max_length=100)

    phone = models.CharField(max_length=20)

    email = models.EmailField(unique=True)

    account_number = models.CharField(
        max_length=20,
        unique=True
    )

    wallet_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    location = models.CharField(max_length=255)

    pppoe_username = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clients_created'
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients_updated'
    )



    def save(self, *args, **kwargs):

        if self.phone:

            phone = self.phone.strip()

            if phone.startswith('07'):

                self.phone = (
                    '+254' + phone[1:]
                )

            elif phone.startswith('254'):

                self.phone = (
                    '+' + phone
                )
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.account_number:

            self.account_number = f"NXV-{1000 + self.id}"

            super().save(update_fields=['account_number'])

    def __str__(self):

        return self.name
    

#PACKAGE MODEL
class Package(models.Model):
    name = models.CharField(max_length=100)
    speed = models.CharField(max_length=50)  # e.g. 10Mbps
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.IntegerField()  # e.g. 30 days

    def __str__(self):
        return f"{self.name} - {self.speed}"

#SUBSCRIPTION MODEL
class Subscription(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    amount = models.DecimalField(max_digits=8, decimal_places=2)

    start_date = models.DateField(auto_now_add=True)

    end_date = models.DateField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('suspended', 'Suspended'),
            ('inactive', 'Inactive')
        ],
        default='active'
    )

    def save(self, *args, **kwargs):

        if self.package:
            self.amount = self.package.price

            if not self.end_date:
                self.end_date = date.today() + timedelta(
                    days=self.package.duration_days
                )

        super().save(*args, **kwargs)

    def is_active(self):

        return (
            self.end_date
            and self.end_date >= date.today()
            and self.status == 'active'
        )

    def __str__(self):

        if self.package:
            return f"{self.client.name} - {self.package.name}"

        return f"{self.client.name} - No Package"


# SUBSCRIPTION EXTENSION LOG
class ExtensionLog(models.Model):

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='extension_logs'
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='extension_logs'
    )

    days_added = models.PositiveIntegerField(
        help_text="Number of days added to the subscription."
    )

    previous_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expiry date before the extension was applied."
    )

    new_end_date = models.DateField(
        help_text="New expiry date after the extension was applied."
    )

    reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for the extension."
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_extensions',
        help_text="Admin user who performed the extension."
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "-created_at"
        ]

        verbose_name = "Extension Log"

        verbose_name_plural = "Extension Logs"

    def __str__(self):

        return (
            f"{self.client.name} - "
            f"{self.days_added} day extension - "
            f"{self.created_at}"
        )
#MIKROTIK LOG MODEL
class MikroTikLog(models.Model):

    ACTION_CHOICES = [
        ('activated', 'Activated'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    pppoe_username = models.CharField(max_length=100)

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):

        return (
            f"{self.client.name} - "
            f"{self.action} - "
            f"{self.created_at}"
        )
    
#NotificationLog model
class NotificationLog(models.Model):

    NOTIFICATION_TYPES = [
        ('expiring', 'Expiring'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('payment_confirmation', 'Payment Confirmation'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )

    message = models.TextField()

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    delivery_status = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    gateway_message_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    gateway_response = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):

        return (
            f"{self.client.name} - "
            f"{self.notification_type} - "
            f"{self.created_at}"
        )


#payment transaction model
class Payment(models.Model):

    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('cash', 'Cash'),
        ('bank', 'Bank'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    transaction_code = models.CharField(
        max_length=100,
        unique=True
    )

    account_reference = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='mpesa'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('underpaid', 'Underpaid'),
            ('credit', 'Credit'),
        ],
        default='pending'
    )

    
    def __str__(self):

        return (
            f"{self.client.name} - "
            f"{self.amount} - "
            f"{self.transaction_code}"
        )
    
#MPESA_TRANSACTION MODEL
class MpesaTransaction(models.Model):

    receipt_number = models.CharField(
        max_length=50,
        unique=True
    )

    account_reference = models.CharField(
        max_length=50
    )

    phone_number = models.CharField(
        max_length=20
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    raw_payload = models.JSONField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    callback_processed = models.BooleanField(
        default=False
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    processing_status = models.CharField(
        max_length=20,
        default='pending'
    )

    def __str__(self):

        return (
            f"{self.receipt_number} - "
            f"{self.account_reference}"
        )

#STK PUSH TRANSACTION MODEL
class StkPushRequest(models.Model):

    merchant_request_id = models.CharField(
        max_length=255,
        unique=True
    )

    checkout_request_id = models.CharField(
        max_length=255,
        unique=True
    )

    account_reference = models.CharField(
        max_length=20,
        db_index=True
    )

    phone_number = models.CharField(
        max_length=20,
        db_index=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
        db_index=True
    )

    response_code = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    response_description = models.TextField(
        blank=True,
        null=True
    )

    raw_response = models.JSONField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = ['-created_at']

        verbose_name = "STK Push Request"

        verbose_name_plural = "STK Push Requests"

    def __str__(self):

        return (
            f"{self.account_reference} | "
            f"KES {self.amount} | "
            f"{self.status}"
        )

#invoice model
class Invoice(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    INVOICE_TYPES = [
        ('subscription', 'Subscription'),
        ('equipment', 'Equipment'),
        ('service', 'Service'),
        ('other', 'Other'),
    ]

    invoice_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )

    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPES,
        default='subscription'
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    balance_due = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    due_date = models.DateField()

    billing_period_start = models.DateField(
        null=True,
        blank=True
    )

    billing_period_end = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    renewal_processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this subscription invoice triggered a renewal."
    )

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        super().save(*args, **kwargs)

        if is_new and not self.invoice_number:

            self.invoice_number = (
                f"INV-{1000 + self.id}"
            )

            super().save(
                update_fields=['invoice_number']
            )

    def update_payment_status(self):

        self.balance_due = (
            self.amount - self.amount_paid
        )

        if self.balance_due <= 0:

            self.balance_due = 0

            self.status = 'paid'

        elif self.due_date < timezone.now().date():

            self.status = 'overdue'

        else:

            self.status = 'pending'

        self.save(
            update_fields=[
                'amount_paid',
                'balance_due',
                'status'
            ]
        )

    def __str__(self):

        return (
            f"{self.invoice_number} - "
            f"{self.client.name}"
        )
    
# PAYMENT ALLOCATION MODEL

class PaymentAllocation(models.Model):
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.CASCADE,
        related_name="allocations"
    )
    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.CASCADE,
        related_name="payment_allocations"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    allocated_at = models.DateTimeField(
        auto_now_add=True
    )
    # NEW: Reversal tracking fields
    is_reversed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Flag indicating if this allocation was reversed/unallocated."
    )
    reversed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    reversal_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for unallocation or payment refund."
    )

    class Meta:
        ordering = ["-allocated_at"]
        verbose_name = "Payment Allocation"
        verbose_name_plural = "Payment Allocations"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="payment_allocation_amount_positive"
            )
        ]

    def __str__(self):
        status = " [REVERSED]" if self.is_reversed else ""
        return (
            f"{self.payment.transaction_code} -> "
            f"{self.invoice.invoice_number} - "
            f"KES {self.amount}{status}"
        )

# Wallet allocation model
class WalletAllocation(models.Model):

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="wallet_allocations"
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="wallet_allocations"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    allocated_at = models.DateTimeField(
        auto_now_add=True
    )

    # Reversal tracking
    is_reversed = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Flag indicating whether this wallet allocation "
            "was reversed."
        )
    )

    reversed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reversal_reason = models.TextField(
        blank=True,
        null=True,
        help_text=(
            "Reason for reversing this wallet allocation."
        )
    )

    class Meta:

        ordering = ["-allocated_at"]

        verbose_name = "Wallet Allocation"
        verbose_name_plural = "Wallet Allocations"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="wallet_allocation_amount_positive"
            )
        ]

    def __str__(self):

        status = (
            " [REVERSED]"
            if self.is_reversed
            else ""
        )

        return (
            f"{self.client.account_number} -> "
            f"{self.invoice.invoice_number} - "
            f"KES {self.amount}{status}"
        )
    