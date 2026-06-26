import os
import sys
from datetime import date

sys.path.append(
    '/home/kimkali/projects'
)

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'isp_system.settings'
)

import django
django.setup()

from clients.models import NotificationLog

from services.sms_service import (
    send_sms
)

from services.notification_service import (
    get_expiring_subscriptions,
    get_expired_subscriptions,
    get_suspended_subscriptions,

    build_expiring_message,
    build_expired_message,
    build_suspended_message
)

#Reusable Helper Function
def log_and_send(
    subscription,
    notification_type,
    message
):

    already_sent = (
        NotificationLog.objects.filter(
            client=subscription.client,
            notification_type=notification_type,
            created_at__date=date.today()
        ).exists()
    )

    if already_sent:

        print(
            f"SKIPPED -> "
            f"{subscription.client.name} "
            f"({notification_type})"
        )

        return

    result = send_sms(

        subscription.client.phone,

        message,
        
        sender_id="NEXAVO"
    )

    NotificationLog.objects.create(

        client=subscription.client,

        notification_type=notification_type,

        message=message,

        phone_number=subscription.client.phone,

        delivery_status=result.get(
            "status"
        ),

        gateway_message_id=result.get(
            "message_id"
        ),

        gateway_response=str(result)
    )

    print(

        f"SENT -> "

        f"{subscription.client.name} "

        f"({notification_type})"
    )

#Send Expiring Notifications
def send_expiring_notifications():

    for subscription in (

        get_expiring_subscriptions()
    ):

        message = (

            build_expiring_message(
                subscription
            )
        )

        log_and_send(

            subscription,

            'expiring',

            message
        )

#Send Notifications for expired 
def send_expired_notifications():

    for subscription in (

        get_expired_subscriptions()
    ):

        message = (

            build_expired_message(
                subscription
            )
        )

        log_and_send(

            subscription,

            'expired',

            message
        )

#Send notifications for suspended 
def send_suspended_notifications():

    for subscription in (

        get_suspended_subscriptions()
    ):

        message = (

            build_suspended_message(
                subscription
            )
        )

        log_and_send(

            subscription,

            'suspended',

            message
        )



if __name__ == "__main__":

    print(
        "\nSending Expiring Notifications\n"
    )

    send_expiring_notifications()

    print(
        "\nSending Expired Notifications\n"
    )

    send_expired_notifications()

    print(
        "\nSending Suspended Notifications\n"
    )

    send_suspended_notifications()

