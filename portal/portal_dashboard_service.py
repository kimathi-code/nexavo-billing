from portal.models import PortalAccount
from datetime import date
from clients.models import (
    Subscription,
    Payment,
)

def get_subscription(client):
    """
    Return the customer's active subscription.
    """

    subscription = (
        Subscription.objects
        .filter(
            client=client
        )
        .order_by(
            "-end_date"
        )
        .first()
    )

    if not subscription:

        return None

    days_remaining = None

    if subscription.end_date:

        days_remaining = (
            subscription.end_date
            - date.today()
        ).days

    return {

        "object": subscription,

        "package": (
            subscription.package.name
            if subscription.package
            else "No Package"
        ),

        "speed": (
            subscription.package.speed
            if subscription.package
            else None
        ),

        "status": subscription.status.title(),

        "amount": subscription.amount,

        "start_date": subscription.start_date,

        "end_date": subscription.end_date,

        "days_remaining": days_remaining,

        "is_active": subscription.is_active(),
    }


def get_wallet(client):

    return {

        "balance": client.wallet_balance,

        "currency": "KES",

        "formatted_balance": (
            f"KES {client.wallet_balance:,.2f}"
        )
    }


def get_recent_payments(
    client,
    limit=5
):
    """
    Return recent customer payments.
    """

    payments = (
        Payment.objects
        .filter(
            client=client,
            status="completed"
        )
        .order_by(
            "-created_at"
        )[:limit]
    )

    return [

        {

            "date": payment.created_at,

            "amount": payment.amount,

            "receipt": payment.transaction_code,

            "method": payment.get_payment_method_display(),

            "status": payment.status.title(),
        }

        for payment in payments

    ]


def get_recent_invoices(client):
    """
    Return recent invoices.

    Placeholder.
    """

    return []


def get_router_status(client):
    """
    Return RouterOS connection status.

    Placeholder.
    """

    return {
        "connected": False,
        "last_seen": None
    }


def get_notifications(client):
    """
    Return recent notifications.

    Placeholder.
    """

    return []


def calculate_account_summary(
    client,
    subscription
):
    """
    Build summary values for dashboard cards.
    """

    return {

        "account_number": client.account_number,

        "wallet_balance": (
            f"KES {client.wallet_balance:,.2f}"
        ),

        "phone": client.phone,

        "subscription_status": (
            subscription["status"]
            if subscription
            else "No Active Subscription"
        )
    }


def get_dashboard_data(user):
    """
    Build complete dashboard context.
    """

    portal_account = user.portal_account

    client = portal_account.client

    subscription = get_subscription(client)

    wallet = get_wallet(client)

    payments = get_recent_payments(client)

    invoices = get_recent_invoices(client)

    router = get_router_status(client)

    notifications = get_notifications(client)

    summary = calculate_account_summary(
        client,
        subscription
    )

    return {

        "portal_account": portal_account,

        "client": client,

        "subscription": subscription,

        "wallet": wallet,

        "payments": payments,

        "invoices": invoices,

        "router": router,

        "notifications": notifications,

        "summary": summary,
    }