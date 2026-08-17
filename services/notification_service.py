from datetime import date, timedelta

from clients.models import Subscription, Invoice

from services.invoice_service import (
    calculate_required_top_up,
)
# helper functions to get relevant invoices
def get_notification_invoice(subscription):
    """
    Return the pending invoice associated with
    the subscription.
    """

    return (
        Invoice.objects
        .filter(
            subscription=subscription,
            status="pending",
        )
        .order_by(
            "due_date",
            "created_at",
        )
        .first()
    )

def get_expiring_subscriptions(days=7):

    today = date.today()

    target_date = (
        today + timedelta(days=days)
    )

    return Subscription.objects.filter(
        status='active',
        end_date__range=(
            today,
            target_date
        )
    )


def get_expired_subscriptions():

    return Subscription.objects.filter(
        status='expired'
    )


def get_suspended_subscriptions():

    return Subscription.objects.filter(
        status='suspended'
    )

#EXPIRING MESSAGE BUILDER
def build_expiring_message(subscription):
    """
    Build an expiry notification using the
    subscription's pending invoice.
    """

    invoice = get_notification_invoice(
        subscription
    )

    wallet_balance = (
        subscription.client.wallet_balance
    )

    expiry_date = (
        subscription.end_date.strftime(
            "%d %b %Y"
        )
    )

    # No pending invoice found.
    if not invoice:

        return (
            f"Dear {subscription.client.name}, "
            f"your internet expires on {expiry_date}. "
            f"Please ensure your wallet has sufficient "
            f"funds for automatic renewal. Nexavo."
        )

    top_up_required = calculate_required_top_up(
        invoice,
        wallet_balance,
    )

    # CUSTOMER ALREADY HAS ENOUGH FUNDS
    if top_up_required == 0:

        return (
            f"Dear {subscription.client.name}, "
            f"your internet expires on {expiry_date}. "
            f"Nexavo Acc. Bal: "
            f"KES {wallet_balance:.2f}. "
            f"Sufficient for auto-renewal. "
            f"Thank you from Nexavo."
        )

    # CUSTOMER NEEDS TO TOP UP
    return (
        f"Dear {subscription.client.name}, "
        f"your internet expires on {expiry_date}. "
        f"To avoid disconnection, pay "
        f"KES {top_up_required:.2f} via "
        f"Paybill 5489004, "
        f"Acc: {subscription.client.account_number}. "
        f"Nexavo."
    )

#EXPIRED MESSAGE BUILDER
def build_expired_message(subscription):
    """
    Build an expired subscription notification
    using the subscription's invoice.
    """

    invoice = (
        Invoice.objects
        .filter(
            subscription=subscription,
        )
        .order_by(
            "-created_at",
        )
        .first()
    )

    expiry_date = (
        subscription.end_date.strftime(
            "%d %b %Y"
        )
    )

    if not invoice:

        return (
            f"Dear {subscription.client.name}, "
            f"your internet expired on {expiry_date}. "
            f"Please contact Nexavo for reactivation."
        )

    wallet_balance = (
        subscription.client.wallet_balance
    )

    top_up_required = calculate_required_top_up(
        invoice,
        wallet_balance,
    )

    return (
        f"Dear {subscription.client.name}, "
        f"your internet expired on {expiry_date}. "
        f"Pay KES {top_up_required:.2f} via "
        f"Paybill 5489004, "
        f"Acc: {subscription.client.account_number} "
        f"to reactivate. Nexavo."
    )
#SUSPENDED MESSAGE BUILDER
def build_suspended_message(subscription):
    """
    Build a suspended subscription notification
    using the subscription's invoice.
    """

    invoice = (
        Invoice.objects
        .filter(
            subscription=subscription,
        )
        .order_by(
            "-created_at",
        )
        .first()
    )

    if not invoice:

        return (
            f"Dear {subscription.client.name}, "
            f"your internet is suspended. "
            f"Please contact Nexavo for assistance. "
            f"Help: 0791018986."
        )

    wallet_balance = (
        subscription.client.wallet_balance
    )

    top_up_required = calculate_required_top_up(
        invoice,
        wallet_balance,
    )

    return (
        f"Dear {subscription.client.name}, "
        f"your internet is suspended. "
        f"Pay KES {top_up_required:.2f} via "
        f"Paybill 5489004, "
        f"Acc: {subscription.client.account_number} "
        f"to reactivate. "
        f"Help: 0791018986. Nexavo."
    )