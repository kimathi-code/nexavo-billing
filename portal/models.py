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
