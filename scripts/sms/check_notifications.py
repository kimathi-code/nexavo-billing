import os
import sys

sys.path.append(
    '/home/kimkali/projects'
)

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'isp_system.settings'
)

import django
django.setup()

from services.notification_service import (
    get_expiring_subscriptions,
    get_expired_subscriptions,
    get_suspended_subscriptions,
    build_expiring_message,
    build_expired_message,
    build_suspended_message
)
from clients.models import NotificationLog


def run_check():

    print("\nEXPIRING CLIENTS\n")

    for sub in get_expiring_subscriptions():

        message = (
            build_expiring_message(sub)
        )

        print(message)

        NotificationLog.objects.create(
            client=sub.client,
            notification_type='expiring',
            message=message
        )

        print("-" * 50)

    print("\nEXPIRED CLIENTS\n")

    for sub in get_expired_subscriptions():

        message = (
            build_expired_message(sub)
        )

        print(message)

        NotificationLog.objects.create(
            client=sub.client,
            notification_type='expired',
            message=message
    )

    print("-" * 50)

    print("\nSUSPENDED CLIENTS\n")

    for sub in get_suspended_subscriptions():

        message = (
            build_suspended_message(sub)
        )

        print(message)

        NotificationLog.objects.create(
            client=sub.client,
            notification_type='suspended',
            message=message
        )

        print("-" * 50)


if __name__ == "__main__":

    run_check()
