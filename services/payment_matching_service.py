from dataclasses import dataclass

from clients.models import Client
from hotspot.models import HotspotPurchase


@dataclass
class PaymentMatchResult:
    matched: bool
    payment_type: str | None = None
    client: Client | None = None
    hotspot_purchase: HotspotPurchase | None = None
    message: str = ""


def match_payment_reference(reference):
    """
    Match a Nexavo payment reference to its business owner.

    Supported references:
        NXV-XXXX -> registered Client
        HS-XXXXXX -> HotspotPurchase

    The database record is the source of truth. The prefix is only
    a convention and is not used as the final authority.
    """
    if not reference:
        return PaymentMatchResult(
            matched=False,
            message="Payment reference is required.",
        )

    reference = reference.strip().upper()

    client = Client.objects.filter(
        account_number=reference
    ).first()

    if client:
        return PaymentMatchResult(
            matched=True,
            payment_type="client",
            client=client,
            message="Payment reference matched to registered client.",
        )

    hotspot_purchase = HotspotPurchase.objects.filter(
        payment_reference=reference
    ).first()

    if hotspot_purchase:
        return PaymentMatchResult(
            matched=True,
            payment_type="hotspot",
            hotspot_purchase=hotspot_purchase,
            message="Payment reference matched to hotspot purchase.",
        )

    return PaymentMatchResult(
        matched=False,
        message="Payment reference could not be matched.",
    )