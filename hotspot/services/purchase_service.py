from django.db import transaction
from django.utils import timezone

from hotspot.models import HotspotPlan, HotspotPurchase
from hotspot.services.voucher_service import generate_voucher


class PurchaseServiceError(Exception):
    """Base exception for Hotspot purchase service errors."""


class PurchaseValidationError(PurchaseServiceError):
    """Raised when a Hotspot purchase cannot be created or confirmed."""


def create_hotspot_purchase(
    plan: HotspotPlan,
    payment_method: str,
    phone_number: str | None = None,
) -> HotspotPurchase:
    """
    Create a pending Hotspot purchase.

    The purchase remains pending until payment is confirmed.
    No voucher is generated at this stage.
    """

    if not isinstance(plan, HotspotPlan):
        raise TypeError("plan must be a HotspotPlan instance.")

    if not plan.active:
        raise PurchaseValidationError(
            f"Hotspot plan '{plan.name}' is inactive."
        )

    valid_methods = {
        choice[0]
        for choice in HotspotPurchase.PAYMENT_METHODS
    }

    if payment_method not in valid_methods:
        raise PurchaseValidationError(
            f"Unsupported payment method: {payment_method}"
        )

    if payment_method == "mpesa" and not phone_number:
        raise PurchaseValidationError(
            "Phone number is required for M-Pesa purchases."
        )

    return HotspotPurchase.objects.create(
        plan=plan,
        amount=plan.price,
        payment_method=payment_method,
        phone_number=phone_number,
        status="pending",
    )


@transaction.atomic
def confirm_hotspot_purchase(
    purchase: HotspotPurchase,
    transaction_reference: str,
) -> HotspotPurchase:
    """
    Confirm a pending Hotspot purchase and issue its voucher.

    The operation is idempotent:
    if the purchase has already been paid and has a voucher,
    the existing purchase is returned without creating another voucher.
    """

    if not isinstance(purchase, HotspotPurchase):
        raise TypeError(
            "purchase must be a HotspotPurchase instance."
        )

    if not transaction_reference:
        raise PurchaseValidationError(
            "Transaction reference is required."
        )

    locked_purchase = (
        HotspotPurchase.objects
        .select_for_update()
        .select_related("plan")
        .get(pk=purchase.pk)
    )

    if locked_purchase.status == "paid":
        if locked_purchase.voucher_id:
            return locked_purchase

        raise PurchaseServiceError(
            f"Purchase {locked_purchase.pk} is marked paid "
            "but has no voucher."
        )

    if locked_purchase.status != "pending":
        raise PurchaseValidationError(
            f"Purchase {locked_purchase.pk} cannot be confirmed "
            f"because its status is '{locked_purchase.status}'."
        )

    if not locked_purchase.plan.active:
        raise PurchaseValidationError(
            f"Hotspot plan '{locked_purchase.plan.name}' is inactive."
        )

    voucher = generate_voucher(locked_purchase.plan)

    locked_purchase.voucher = voucher
    locked_purchase.status = "paid"
    locked_purchase.transaction_reference = transaction_reference
    locked_purchase.paid_at = timezone.now()

    locked_purchase.save(
        update_fields=[
            "voucher",
            "status",
            "transaction_reference",
            "paid_at",
        ]
    )

    return locked_purchase