from django.contrib.auth.models import User

from django.utils import timezone

from django.core.exceptions import ValidationError

from portal.models import PortalAccount


def activate_portal_account(
    client,
    username,
    password
):

    if PortalAccount.objects.filter(
        client=client
    ).exists():

        raise ValidationError(
            "Portal account already activated."
        )

    if User.objects.filter(
        username=username
    ).exists():

        raise ValidationError(
            "Username already exists. Please choose another username."
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