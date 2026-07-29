"""
Payment dashboard services.

Provides payment data for:

- Dashboard
- Payments page
- Future payment analytics
"""

from clients.models import Payment


def get_recent_payments(
    client,
    limit=5,
):
    """
    Return recent customer payments.
    """

    payments = (
        Payment.objects
        .filter(
            client=client,
            status="completed",
        )
        .order_by(
            "-created_at",
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

            "method": (
                payment.get_payment_method_display()
            ),

            "status": payment.status.title(),

        }

        for payment in payments

    ]


def get_payment_history(
    client,
):
    """
    Return complete payment history.

    Placeholder for the Payments page.
    """

    return get_recent_payments(
        client,
        limit=1000,
    )


def get_payment_summary(
    client,
):
    """
    Placeholder for payment analytics.

    Future:

    - Total paid
    - Preferred payment method
    - Last payment
    - Payment count
    """

    return {}
