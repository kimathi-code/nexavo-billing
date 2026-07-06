from django.contrib.auth.models import User

from django.utils import timezone

from django.core.exceptions import ValidationError

from clients.models import Client

from portal.models import PortalAccount


def activate_portal_account(
    account_number,
    phone_number,
    username,
    password
):

    client = Client.objects.get(
        account_number=account_number,
        phone=phone_number
    )
    
    if PortalAccount.objects.filter(
        client=client
    ).exists():

        raise ValidationError(
            "Portal account already activated."
        )

    user = User.objects.create_user(
        username=username,
        password=password
    )


    portal_account = (
        PortalAccount.objects.create(
            user=user,
            client=client,
            is_verified=True,
            activated_at=timezone.now()
        )
    )


    return portal_account
