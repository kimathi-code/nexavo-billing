import random
from datetime import timedelta

from django.utils import timezone

from django.db import models

from django.contrib.auth.models import User

from clients.models import Client


class PortalAccount(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="portal_account"
    )

    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name="portal_account"
    )

    is_verified = models.BooleanField(
        default=False
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):

        return (
            f"{self.client.name} Portal Account"
        )

# OTP Model
class PortalActivationOTP(models.Model):
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="portal_otps"
    )

    code = models.CharField(
        max_length=6
    )

    is_used = models.BooleanField(
        default=False
    )

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    PURPOSE_CHOICES = [
        (
            "activation",
            "Activation"
        ),

        (
            "password_reset",
            "Password Reset"
        ),
    ]


    purpose = models.CharField(
        max_length=30,
        choices=PURPOSE_CHOICES,
        default="activation"
    )

    def has_expired(self):
        return timezone.now() > self.expires_at


    @classmethod
    def generate(
        cls,
        client,
        purpose="activation"
    ):
        otp = str(
            random.randint(
                100000,
                999999
            )
        )

        return cls.objects.create(
            client=client,
            code=otp,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=10)
        )


    def __str__(self):
        return f"{self.client.account_number} OTP"
    