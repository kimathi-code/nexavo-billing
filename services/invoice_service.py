from clients.models import Invoice
import logging

logger = logging.getLogger("invoice")

def get_pending_invoice(client):
    """
    Return the oldest pending invoice
    for the client.
    """

    return (
        Invoice.objects
        .filter(
            client=client,
            status="pending",
        )
        .order_by(
            "due_date",
            "created_at",
        )
        .first()
    )


def apply_payment_to_invoice(
    invoice,
    payment_amount,
):
    """
    Apply an actual payment to an invoice.
    """

    invoice.amount_paid += payment_amount

    invoice.update_payment_status()
    logger.info(
        "Applied %s to invoice %s.",
        payment_amount,
        invoice.invoice_number,
    )

    return invoice

def calculate_required_top_up(
    invoice,
    wallet_balance,
):
    """
    Calculate how much additional wallet funding
    is required to cover an invoice.

    Paid invoices require no additional funding.
    """

    if invoice.status == "paid":

        return 0

    top_up_required = (
        invoice.balance_due - wallet_balance
    )

    if top_up_required < 0:

        top_up_required = 0

    return top_up_required
