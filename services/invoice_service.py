from decimal import Decimal
import logging

from django.db import transaction

from clients.models import Invoice, InvoiceItem

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


@transaction.atomic
def create_itemized_invoice(
    client,
    items,
    due_date,
    invoice_type="other",
):
    """
    Create an invoice together with its invoice items.

    Each item must contain:
        description
        quantity
        unit_price
        item_type

    Item totals and the final invoice total are calculated
    by this service.
    """

    if not items:
        raise ValueError(
            "At least one invoice item is required."
        )

    valid_invoice_types = dict(Invoice.INVOICE_TYPES)

    if invoice_type not in valid_invoice_types:
        raise ValueError(
            f"Invalid invoice type: {invoice_type}"
        )

    valid_item_types = dict(InvoiceItem.ITEM_TYPES)

    invoice_total = Decimal("0.00")
    calculated_items = []

    for item in items:
        description = item.get("description")
        quantity = item.get("quantity")
        unit_price = item.get("unit_price")
        item_type = item.get("item_type")

        if not description:
            raise ValueError(
                "Invoice item description is required."
            )

        if quantity is None or quantity <= 0:
            raise ValueError(
                "Invoice item quantity must be greater than zero."
            )

        if unit_price is None:
            raise ValueError(
                "Invoice item unit price is required."
            )

        unit_price = Decimal(str(unit_price))

        if unit_price < 0:
            raise ValueError(
                "Invoice item unit price cannot be negative."
            )

        if item_type not in valid_item_types:
            raise ValueError(
                f"Invalid invoice item type: {item_type}"
            )

        quantity = int(quantity)
        total = quantity * unit_price

        calculated_items.append({
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "total": total,
            "item_type": item_type,
        })

        invoice_total += total

    if invoice_total <= Decimal("0.00"):
        raise ValueError(
            "Invoice total must be greater than zero."
        )

    invoice = Invoice.objects.create(
        client=client,
        invoice_type=invoice_type,
        amount=invoice_total,
        balance_due=invoice_total,
        due_date=due_date,
    )

    InvoiceItem.objects.bulk_create([
        InvoiceItem(
            invoice=invoice,
            **item_data,
        )
        for item_data in calculated_items
    ])

    logger.info(
        "Created invoice %s for account %s. "
        "Type: %s | Total: KES %s | Items: %s.",
        invoice.invoice_number,
        client.account_number,
        invoice_type,
        invoice_total,
        len(calculated_items),
    )

    return invoice

def create_equipment_invoice(
    client,
    items,
    due_date,
):
    """
    Create an equipment invoice from itemized equipment charges.
    """

    equipment_items = [
        {
            **item,
            "item_type": "equipment",
        }
        for item in items
    ]

    return create_itemized_invoice(
        client=client,
        items=equipment_items,
        due_date=due_date,
        invoice_type="equipment",
    )


def create_service_invoice(
    client,
    items,
    due_date,
):
    """
    Create a service invoice from itemized service charges.
    """

    service_items = [
        {
            **item,
            "item_type": "service",
        }
        for item in items
    ]

    return create_itemized_invoice(
        client=client,
        items=service_items,
        due_date=due_date,
        invoice_type="service",
    )
