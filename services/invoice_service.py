from clients.models import Invoice


def apply_payment_to_invoice(
    invoice,
    payment_amount
):

    invoice.amount_paid += payment_amount

    invoice.update_payment_status()

    return invoice
