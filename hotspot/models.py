import re
import secrets
import string
from django.db import models
from django.core.exceptions import ValidationError


# Hotspot location model

# A voucher will not belong permanently to a location.
class HotspotLocation(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Hotspot Location"
        verbose_name_plural = "Hotspot Locations"

    def __str__(self):
        return self.name

# Hotspot plan model
# plan can be either "time" or "data".
class HotspotPlan(models.Model):
    name = models.CharField(max_length=100)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum duration of the plan in minutes."
    )

    data_limit_mb = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum data allowance in MB."
    )

    download_speed_kbps = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Download speed limit in Kbps."
    )

    upload_speed_kbps = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Upload speed limit in Kbps."
    )

    simultaneous_devices = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of devices allowed at the same time."
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price", "name"]
        verbose_name = "Hotspot Plan"
        verbose_name_plural = "Hotspot Plans"

    def __str__(self):
        return f"{self.name} - KES {self.price}"


# HotspotVoucher model
class HotspotVoucher(models.Model):
    STATUS_CHOICES = [
        ("generated", "Generated"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("disabled", "Disabled"),
    ]

    code = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
    )

    plan = models.ForeignKey(
        HotspotPlan,
        on_delete=models.PROTECT,
        related_name="vouchers"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="generated",
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    bound_mac = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        editable=False,
        help_text="Device MAC address permanently bound while the voucher is active."
    )

    data_used_mb = models.PositiveIntegerField(
        default=0,
        editable=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Hotspot Voucher"
        verbose_name_plural = "Hotspot Vouchers"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status="generated", activated_at__isnull=True)
                    & models.Q(expires_at__isnull=True)
                )
                | (
                    models.Q(
                        status__in=["active", "expired"],
                        activated_at__isnull=False,
                        expires_at__isnull=False,
                    )
                )
                | models.Q(status="disabled"),
                name="hotspot_voucher_valid_activation_state",
            ),
        ]

    def __str__(self):
        return self.code

    @staticmethod
    def generate_code():
        alphabet = string.ascii_uppercase + string.digits

        while True:
            part_one = "".join(
                secrets.choice(alphabet)
                for _ in range(4)
            )
            part_two = "".join(
                secrets.choice(alphabet)
                for _ in range(4)
            )

            code = f"NXV-HS-{part_one}-{part_two}"

            if not HotspotVoucher.objects.filter(code=code).exists():
                return code

    @staticmethod
    def normalize_mac(mac_address):
        if not mac_address:
            raise ValueError("MAC address is required.")

        mac = mac_address.strip().upper()

        # Accept:
        # AA:BB:CC:DD:EE:FF
        # AA-BB-CC-DD-EE-FF
        # AABBCCDDEEFF
        mac = re.sub(r"[:-]", "", mac)

        if not re.fullmatch(r"[0-9A-F]{12}", mac):
            raise ValueError("Invalid MAC address.")

        return ":".join(
            mac[i:i + 2]
            for i in range(0, 12, 2)
        )

    def clean(self):
        super().clean()

        if self.status == "generated":
            if self.activated_at is not None:
                raise ValidationError(
                    "A generated voucher cannot have an activation time."
                )

            if self.expires_at is not None:
                raise ValidationError(
                    "A generated voucher cannot have an expiry time."
                )

            if self.bound_mac:
                raise ValidationError(
                    "A generated voucher cannot have a bound MAC address."
                )

        if self.status in ["active", "expired"]:
            if self.activated_at is None:
                raise ValidationError(
                    "An active or expired voucher must have an activation time."
                )

            if self.expires_at is None:
                raise ValidationError(
                    "An active or expired voucher must have an expiry time."
                )

            if not self.bound_mac:
                raise ValidationError(
                    "An active or expired voucher must have a bound MAC address."
                )

            self.bound_mac = self.normalize_mac(self.bound_mac)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()

        if self.bound_mac:
            self.bound_mac = self.normalize_mac(self.bound_mac)

        self.full_clean()

        super().save(*args, **kwargs)
# Hotspot purchase model
class HotspotPurchase(models.Model):
    PAYMENT_METHODS = [
        ("mpesa", "M-Pesa"),
        ("cash", "Cash"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    plan = models.ForeignKey(
        HotspotPlan,
        on_delete=models.PROTECT,
        related_name="purchases"
    )

    voucher = models.OneToOneField(
        HotspotVoucher,
        on_delete=models.PROTECT,
        related_name="purchase",
        null=True,
        blank=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS
    )

    transaction_reference = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Hotspot Purchase"
        verbose_name_plural = "Hotspot Purchases"

    def __str__(self):
        return f"{self.plan.name} - KES {self.amount}"

# Hotspot session model
class HotspotSession(models.Model):
    voucher = models.ForeignKey(
        HotspotVoucher,
        on_delete=models.PROTECT,
        related_name="sessions"
    )

    location = models.ForeignKey(
        HotspotLocation,
        on_delete=models.PROTECT,
        related_name="sessions"
    )

    username = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    mac_address = models.CharField(
        max_length=17
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )

    started_at = models.DateTimeField()

    ended_at = models.DateTimeField(
        blank=True,
        null=True
    )

    bytes_in = models.BigIntegerField(
        default=0
    )

    bytes_out = models.BigIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Hotspot Session"
        verbose_name_plural = "Hotspot Sessions"

    def __str__(self):
        return f"{self.voucher.code} - {self.mac_address}"
