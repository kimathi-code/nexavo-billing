from datetime import timedelta

from django.utils import timezone

from clients.models import (
    Client,
    Subscription,
    Package,
    MikroTikLog
)

from scripts.mikrotik.services import (
    get_mikrotik_api,
    enable_ppp_secret,
    disconnect_active_session
)


def renew_subscription(
    client,
    package,
    payment_amount
):

    today = timezone.now().date()

    subscription = (
        Subscription.objects
        .filter(client=client)
        .order_by('-end_date')
        .first()
    )

    # EXISTING SUBSCRIPTION
    if subscription:

        # If still active, extend from current end date
        if subscription.end_date and subscription.end_date >= today:

            subscription.end_date += timedelta(
                days=package.duration_days
            )

        # If expired, renew from today
        else:

            subscription.start_date = today

            subscription.end_date = (
                today + timedelta(
                    days=package.duration_days
                )
            )

        subscription.package = package

        subscription.amount = payment_amount

        subscription.status = 'active'

        subscription.save()

    # NEW SUBSCRIPTION
    else:

        subscription = Subscription.objects.create(

            client=client,

            package=package,

            amount=payment_amount,

            start_date=today,

            end_date=(
                today + timedelta(
                    days=package.duration_days
                )
            ),

            status='active'
        )

    # MIKROTIK ACTIVATION
    username = client.pppoe_username

    if username:

        api, connection = get_mikrotik_api()

        try:

            enable_ppp_secret(username, api)

            disconnect_active_session(
                username,
                api
            )

            MikroTikLog.objects.create(
                client=client,
                pppoe_username=username,
                action='activated',
                message=(
                    "Subscription renewed "
                    "and PPPoE enabled"
                )
            )

        finally:

            connection.disconnect()

    return subscription
