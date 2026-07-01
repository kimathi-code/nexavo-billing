import os
import sys
from datetime import date


# Setup Django environment
sys.path.append('/home/kimkali/projects')

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'isp_system.settings'
)

import django
django.setup()

# IMPORT DJANGO MODELS AFTER django.setup()
from clients.models import Subscription, MikroTikLog

from scripts.mikrotik.connect import get_mikrotik_api

from scripts.mikrotik.mikrotik_services import (
    disable_ppp_secret,
    disconnect_active_session
)


def run_expiry_check():

    expired_subscriptions = Subscription.objects.filter(
        end_date__lt=date.today(),
        status='active'
    )

    if not expired_subscriptions.exists():

        print("No expired subscriptions found today.")
        return

    # OPEN ONE CONNECTION
    api, connection = get_mikrotik_api()

    for subscription in expired_subscriptions:

        username = subscription.client.pppoe_username

        if username:

            print(f"Processing expiration for: {username}")

            disable_ppp_secret(username, api)
            disconnect_active_session(username, api)

            subscription.status = 'expired'
            subscription.save()

            # Log the disconnection in MikroTikLog model for auditing purposes 
            MikroTikLog.objects.create(
                client=subscription.client,
                pppoe_username=username,
                action='disconnected',
                message=(
                    f"PPPoE user {username} "
                    f"disconnected due to expired subscription."
                )
            )

        else:

            print(
                f"Skipping subscription ID "
                f"{subscription.id}: "
                f"No PPPoE username assigned."
            )

    # CLOSE CONNECTION ONCE
    connection.disconnect()

    print("Finished processing expired subscriptions.")


if __name__ == "__main__":

    run_expiry_check()