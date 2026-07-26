from portal.models import PortalAccount
from datetime import date
from clients.models import (
    Subscription,
    Payment,
    Invoice
)
from scripts.mikrotik.connect import get_mikrotik_api
from scripts.mikrotik.mikrotik_services import get_active_session

#******DATA LOADING FUNCTIONS******
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

            "formatted_amount": (
                f"KES {payment.amount:,.2f}"
            ),

            "receipt": payment.transaction_code,

            "method": payment.get_payment_method_display(),

            "status": payment.status.title(),

        }

        for payment in payments

    ]


def get_recent_invoices(
    client,
    limit=5,
):
    """
    Return recent customer invoices.
    """

    invoices = (
        Invoice.objects
        .filter(client=client)
        .order_by("-created_at")[:limit]
    )

    today = date.today()

    invoice_list = []

    for invoice in invoices:

        days_until_due = (
            invoice.due_date - today
        ).days

        if days_until_due > 0:

            due_message = (
                f"Due in {days_until_due} days"
            )

        elif days_until_due == 0:

            due_message = "Due today"

        else:

            due_message = (
                f"Overdue by {abs(days_until_due)} days"
            )

        invoice_list.append(

            {

                "invoice_number": invoice.invoice_number,

                "amount": invoice.amount,

                "formatted_amount": (
                    f"KES {invoice.amount:,.2f}"
                ),

                "amount_paid": invoice.amount_paid,

                "formatted_amount_paid": (
                    f"KES {invoice.amount_paid:,.2f}"
                ),

                "balance_due": invoice.balance_due,

                "formatted_balance_due": (
                    f"KES {invoice.balance_due:,.2f}"
                ),

                "status": (
                    invoice.get_status_display()
                ),

                "due_date": invoice.due_date,

                "billing_period_start": (
                    invoice.billing_period_start
                ),

                "billing_period_end": (
                    invoice.billing_period_end
                ),

                "created_at": invoice.created_at,

                "days_until_due": days_until_due,

                "due_message": due_message,

                "is_overdue": (
                    invoice.due_date < today
                ),

            }

        )

    return invoice_list


def get_router_status(client):
    """
    Retrieve the client's current router connection status.
    """

    if not client.pppoe_username:

        return {

            "connected": False,

            "status": "No PPPoE Username",

            "ip_address": None,

            "uptime": None,

        }

    api = None
    connection = None

    try:

        api, connection = get_mikrotik_api()

        session = get_active_session(
            client.pppoe_username,
            api,
        )

        if session:
            return session

        return {

            "connected": False,

            "status": "Disconnected",

            "ip_address": None,

            "uptime": None,

        }

    except Exception:

        logger.exception(
            "Failed to retrieve router status."
        )

        return {

            "connected": False,

            "status": "Router Unavailable",

            "ip_address": None,

            "uptime": None,

        }

    finally:

        if connection:

            connection.disconnect()


#******DATA BUILDERS FUNCTIONS******

def calculate_account_summary(
    client,
    subscription,
    wallet
):
    """
    Build summary values for dashboard cards.
    """

    return {

        "account_number": client.account_number,

        "wallet_balance": wallet["formatted_balance"],

        "phone": client.phone,

        "subscription_status": (
            subscription["status"]
            if subscription
            else "No Active Subscription"
        )
    }

def get_notifications(
    client,
    subscription,
    invoices,
    payments,
):
    """
    Build dashboard notifications dynamically.
    """

    notifications = []

    #
    # Subscription expiry
    #
    if (
        subscription
        and subscription["days_remaining"] is not None
        and subscription["days_remaining"] <= 7
    ):

        notifications.append(

            {

                "title": "Subscription Expiring",

                "message": (
                    f"Your subscription expires in "
                    f"{subscription['days_remaining']} day(s)."
                ),

                "type": "warning",

                "priority": 2,

                "created_at": None,
            }

        )

    #
    # Overdue invoices
    #
    for invoice in invoices:

        if invoice["is_overdue"]:

            notifications.append(

                {

                    "title": "Invoice Overdue",

                    "message": (
                        f"{invoice['invoice_number']} "
                        f"is overdue. "
                        f"Outstanding balance: "
                        f"{invoice['formatted_balance_due']}."
                    ),

                    "type": "danger",

                    "priority": 1,

                    "created_at": invoice["created_at"],
                }

            )

    #
    # Latest payment
    #
    if payments:

        latest_payment = payments[0]

        notifications.append(

            {

                "title": "Payment Received",

                "message": (
                    f"We received "
                    f"{latest_payment['formatted_amount']} "
                    f"via "
                    f"{latest_payment['method']}."
                ),

                "type": "success",

                "priority": 3,

                "created_at": latest_payment["date"],
            }

        )

    #
    # Default message
    #
    if not notifications:

        notifications.append(

            {

                "title": "Welcome",

                "message": (
                    "Welcome to Nexavo Portal."
                ),

                "type": "info",

                "priority": 4,

                "created_at": None,
            }

        )

    notifications.sort(
        key=lambda notification: (
            notification["priority"]
        )
    )

    return notifications
    


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

    notifications = get_notifications(client, subscription, invoices, payments)

    summary = calculate_account_summary(
        client,
        subscription,
        wallet
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