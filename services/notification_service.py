from datetime import date, timedelta

from clients.models import Subscription


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

    package_price = (
        subscription.package.price
        if subscription.package
        else 0
    )

    wallet_balance = (
        subscription.client.wallet_balance
    )

    top_up_required = (
        package_price - wallet_balance
    )

    if top_up_required < 0:

        top_up_required = 0

    expiry_date = (
        subscription.end_date.strftime(
            "%d %b %Y"
        )
    )

    # CUSTOMER ALREADY HAS ENOUGH FUNDS
    if top_up_required == 0:

        return (
            f"Dear {subscription.client.name}, your internet expires on {expiry_date}. "
            f"Nexavo Acc. Bal: KES {wallet_balance:.2f}. "
            f"Sufficient for auto-renewal. "
            f"Thank you from Nexavo."
        )

    # CUSTOMER NEEDS TO TOP UP
    return (
        f"Dear {subscription.client.name}, your internet expires on {expiry_date}. "
        f"To avoid disconnection, pay KES {top_up_required:.2f} via "
        f"Paybill 5489004, Acc: {subscription.client.account_number}. Nexavo."
    )

#EXPIRED MESSAGE BUILDER
def build_expired_message(subscription):

    package_price = (
        subscription.package.price
        if subscription.package
        else 0
    )

    wallet = (
        subscription.client.wallet_balance
    )

    balance_due = (
        package_price - wallet
    )

    if balance_due < 0:
        balance_due = 0

    expiry_date = (
        subscription.end_date.strftime(
            "%d %b %Y"
        )
    )

    return (
        f"Dear {subscription.client.name}, your internet expired on {expiry_date}. "
        f"Pay KES {balance_due:.2f} via Paybill 5489004, Acc: {subscription.client.account_number} "
        f"to reactivate. Nexavo."
    )

#SUSPENDED MESSAGE BUILDER
def build_suspended_message(subscription):

    package_price = (
        subscription.package.price
        if subscription.package
        else 0
    )

    wallet_balance = (
        subscription.client.wallet_balance
    )

    balance_due = (
        package_price - wallet_balance
    )

    if balance_due < 0:

        balance_due = 0

    return (
        f"Dear {subscription.client.name}, your internet is suspended. "
        f"Pay KES {balance_due:.2f} via Paybill 5489004, Acc: {subscription.client.account_number} "
        f"to reactivate. Help: 0791018986. Nexavo."
    )
