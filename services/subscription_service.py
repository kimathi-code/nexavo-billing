import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from clients.models import (
    Client,
    Subscription,
    Package,
    MikroTikLog,
    ExtensionLog
)
from scripts.mikrotik.connect import get_mikrotik_api
from scripts.mikrotik.mikrotik_services import (
    enable_ppp_secret,
    disconnect_active_session
)

logger = logging.getLogger(__name__)


def activate_subscription_connection(client: Client) -> bool:
    """
    Activate the client's PPPoE connection through MikroTik.

    Returns:
        bool: True if activation and logging succeeded, False otherwise.
    """
    username = client.pppoe_username

    if not username:
        logger.warning(
            "Activation skipped: Client %s has no PPPoE username set.",
            client.id,
        )
        return False

    connection = None
    try:
        api, connection = get_mikrotik_api()

        enabled = enable_ppp_secret(username, api)

        # Handle boolean or response state returned by enable_ppp_secret
        if enabled is False:
            logger.error(
                "Failed to enable PPP secret on MikroTik for user '%s'.",
                username,
            )
            return False

        disconnect_active_session(username, api)

        MikroTikLog.objects.create(
            client=client,
            pppoe_username=username,
            action='activated',
            message="PPPoE service activated successfully."
        )
        return True

    except Exception as e:
        logger.exception(
            "MikroTik activation error for user '%s': %s",
            username,
            e
        )

        MikroTikLog.objects.create(
            client=client,
            pppoe_username=username,
            action='error',
            message=f"Activation failed: {str(e)[:255]}"
        )
        return False

    finally:
        if connection:
            try:
                connection.disconnect()
            except Exception as e:
                logger.error("Error disconnecting MikroTik API connection: %s", e)


@transaction.atomic
def renew_subscription(
    client: Client,
    package: Package,
    payment_amount: Decimal
) -> Subscription:
    """
    Extends or creates a client subscription upon payment 
    and triggers connection activation.
    """
    today = timezone.now().date()

    subscription = (
        Subscription.objects
        .select_for_update()
        .filter(client=client)
        .order_by('-end_date')
        .first()
    )

    # EXISTING SUBSCRIPTION
    if subscription:
        # If still active, extend from current end date
        if subscription.end_date and subscription.end_date >= today:
            subscription.end_date += timedelta(days=package.duration_days)
        # If expired, renew from today
        else:
            subscription.start_date = today
            subscription.end_date = today + timedelta(days=package.duration_days)

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
            end_date=today + timedelta(days=package.duration_days),
            status='active'
        )

    # Trigger connection activation (isolated execution)
    activation_success = (
        activate_subscription_connection(client)
    )

    if not activation_success:

        logger.error(
            "Subscription renewed but MikroTik activation "
            "failed for account %s.",
            client.account_number,
        )

    return subscription

# service extension function
def extend_subscription(
    subscription: Subscription,
    days: int,
    reason: str = None,
    performed_by=None,
) -> Subscription:
    """
    Extend or restore a client subscription.

    Active subscriptions:
        Extend from the existing expiry date.

    Expired or inactive subscriptions:
        Restore from today and add the requested number of days.

    The subscription update and ExtensionLog are committed
    in a database transaction.

    MikroTik activation is performed after the database
    transaction has successfully committed.

    Args:
        subscription:
            Subscription instance to extend or restore.

        days:
            Number of days to add.

        reason:
            Explanation for the administrative extension.

        performed_by:
            User who performed the extension, if applicable.

    Returns:
        The updated Subscription instance.

    Raises:
        ValueError:
            If days is zero or negative.
    """

    if days <= 0:

        raise ValueError(
            "Extension days must be greater than zero."
        )

    with transaction.atomic():

        # Lock the current database row so that
        # concurrent operations cannot modify
        # the same subscription simultaneously.
        locked_subscription = (
            Subscription.objects
            .select_for_update()
            .get(
                pk=subscription.pk
            )
        )

        today = timezone.now().date()

        previous_end_date = (
            locked_subscription.end_date
        )

        is_currently_active = (
            locked_subscription.status == "active"
            and locked_subscription.end_date
            and locked_subscription.end_date >= today
        )

        # Active subscription:
        # extend from the existing expiry date.
        if is_currently_active:

            locked_subscription.end_date += (
                timedelta(days=days)
            )

        # Expired/inactive subscription:
        # restore from today.
        else:

            locked_subscription.start_date = today

            locked_subscription.end_date = (
                today + timedelta(days=days)
            )

        locked_subscription.status = "active"

        locked_subscription.save(
            update_fields=[
                "start_date",
                "end_date",
                "status",
            ]
        )

        ExtensionLog.objects.create(
            subscription=locked_subscription,
            client=locked_subscription.client,
            days_added=days,
            previous_end_date=previous_end_date,
            new_end_date=locked_subscription.end_date,
            reason=(
                reason
                or "Administrative extension"
            ),
            performed_by=performed_by,
        )

    # The database transaction has now committed.
    # MikroTik is deliberately handled outside
    # the transaction because it is an external system.
    activation_success = (
        activate_subscription_connection(
            locked_subscription.client
        )
    )

    if not activation_success:

        logger.error(
            "Subscription extended for account %s, "
            "but MikroTik activation failed.",
            locked_subscription.client.account_number,
        )

    else:

        logger.info(
            "Subscription extended for account %s | "
            "Previous expiry: %s | "
            "New expiry: %s | "
            "Days: %s | "
            "Reason: %s",
            locked_subscription.client.account_number,
            previous_end_date,
            locked_subscription.end_date,
            days,
            reason or "Administrative extension",
        )

    return locked_subscription