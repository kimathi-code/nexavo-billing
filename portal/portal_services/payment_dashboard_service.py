"""
Payment dashboard services.

Provides payment data for:

- Dashboard
- Payments page
- Future payment analytics
"""
from django.utils import timezone
from decimal import Decimal
import logging

from clients.models import (
    Client,
    Payment,
    StkPushRequest,
)

from services.mpesa_service import MpesaService

# reusable service instance
logger = logging.getLogger(__name__)

mpesa_service = MpesaService()

# payment data builder function
def build_payment_data(payment):
    """
    Convert a Payment model into a
    standardized dictionary for the
    customer portal.
    """

    return {

        "object": payment,

        "date": payment.created_at,

        "amount": payment.amount,

        "formatted_amount": (
            f"KES {payment.amount:,.2f}"
        ),

        "receipt": payment.transaction_code,

        "account_reference": (
            payment.account_reference
        ),

        "method": (
            payment.get_payment_method_display()
        ),

        "status": (
            payment.status.title()
        ),

        "payment_method": (
            payment.payment_method
        ),

    }

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

        build_payment_data(payment)

        for payment in payments

    ]

def get_payment_history(client):
    """
    Return complete payment history.
    """

    payments = (
        Payment.objects
        .filter(
            client=client
        )
        .order_by(
            "-created_at"
        )
    )

    return [

        build_payment_data(payment)

        for payment in payments

    ]

def get_payment_summary(client):
    """
    Return payment summary for the
    customer portal.
    """

    latest_payment = (
        Payment.objects
        .filter(
            client=client,
            status="completed",
        )
        .order_by(
            "-created_at",
        )
        .first()
    )

    payment_count = (
        Payment.objects
        .filter(
            client=client,
            status="completed",
        )
        .count()
    )

    if not latest_payment:

        return {

            "last_payment": None,

            "payment_date": None,

            "payment_method": None,

            "payment_status": None,

            "payment_count": 0,

        }

    return {

        "last_payment": (
            f"KES {latest_payment.amount:,.2f}"
        ),

        "payment_date": (
            latest_payment.created_at
        ),

        "payment_method": (
            latest_payment.get_payment_method_display()
        ),

        "payment_status": (
            latest_payment.status.title()
        ),

        "payment_count": payment_count,

    }

# validate payment request
def validate_payment_request(
    account_number,
    amount,
):
    """
    Validate payment request before
    applying business rules.
    """

    try:

        client = Client.objects.get(
            account_number=account_number
        )

    except Client.DoesNotExist:

        logger.warning(
            "Payment validation failed. "
            "Account %s does not exist.",
            account_number,
        )

        return {
            "success": False,
            "message": "Account number not found.",
        }

    try:

        amount = Decimal(amount)

    except Exception:

        logger.warning(
            "Payment validation failed. "
            "Invalid amount '%s' for account %s.",
            amount,
            account_number,
        )

        return {
            "success": False,
            "message": "Invalid payment amount.",
        }

    if amount <= 0:

        logger.warning(
            "Payment validation failed. "
            "Non-positive amount %s for account %s.",
            amount,
            account_number,
        )

        return {
            "success": False,
            "message": "Amount must be greater than zero.",
        }

    logger.info(
        "Payment request validated successfully "
        "for account %s.",
        client.account_number,
    )

    return {
        "success": True,
        "client": client,
        "amount": amount,
    }

def validate_payment_business_rules(
    client,
):
    """
    Validate business rules before
    initiating STK Push.
    """

    recent_request = (
        StkPushRequest.objects
        .filter(
            account_reference=client.account_number,
            status="pending",
        )
        .order_by("-created_at")
        .first()
    )

    if recent_request:

        elapsed = (
            timezone.now()
            - recent_request.created_at
        ).total_seconds()

        if elapsed < 30:

            remaining = int(30 - elapsed)

            logger.info(
                "Duplicate STK Push blocked "
                "for account %s. "
                "Remaining cooldown: %s seconds.",
                client.account_number,
                remaining,
            )

            return {
                "success": False,
                "message": (
                    f"An M-Pesa payment request is already pending. "
                    f"Please wait {remaining} second(s) "
                    f"before requesting another STK Push."
                ),
            }

    logger.info(
        "Payment business validation passed "
        "for account %s.",
        client.account_number,
    )

    return {
        "success": True,
    }
# stk push wrapper
def initiate_mpesa_payment(
    client,
    amount,
):
    """
    Initiate M-Pesa STK Push.
    """

    logger.info(
        "Initiating STK Push for account %s.",
        client.account_number,
    )

    response = mpesa_service.initiate_stk_push(
        client,
        amount,
    )

    if response.get("success"):

        logger.info(
            "STK Push initiated successfully "
            "for account %s.",
            client.account_number,
        )

    else:

        logger.warning(
            "STK Push failed for account %s. "
            "Reason: %s",
            client.account_number,
            response.get("error"),
        )

    return response