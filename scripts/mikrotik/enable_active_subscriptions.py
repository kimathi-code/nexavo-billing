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
    enable_ppp_secret
)


def run_activation_check():

    active_subscriptions = Subscription.objects.filter(
        end_date__gte=date.today(),
        status='expired'
    )

    if not active_subscriptions.exists():

        print("No active subscriptions found.")
        return

    # OPEN ONE CONNECTION
    api, connection = get_mikrotik_api()

    for subscription in active_subscriptions:

        username = subscription.client.pppoe_username

        if username:

            print(f"Processing activation for: {username}")

            enable_ppp_secret(username, api)
            subscription.status = 'active'
            subscription.save()

            # Log the activation in MikroTikLog model for auditing purposes
            MikroTikLog.objects.create(
                client=subscription.client,
                pppoe_username=username,
                action='activated',
                message=(
                    f"PPPoE user {username} "
                    f"activated due to active subscription."
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

    print("Finished processing active subscriptions.")


if __name__ == "__main__":

    run_activation_check()
