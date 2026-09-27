from hotspot.models import HotspotVoucher
from hotspot.services.voucher_service import (
    VoucherActivationError,
    activate_voucher,
)


class VoucherRedemptionError(Exception):
    """Base exception for Hotspot voucher redemption errors."""


def redeem_voucher(
    voucher_code: str,
    mac_address: str,
) -> HotspotVoucher:
    """
    Redeem a generated Hotspot voucher for the first time.

    A successful redemption activates the voucher and binds it
    to the first device MAC address.

    Already-active vouchers are validated against the supplied MAC.
    """

    if not voucher_code:
        raise VoucherRedemptionError(
            "Voucher code is required."
        )

    try:
        voucher = HotspotVoucher.objects.get(
            code=voucher_code.strip().upper()
        )
    except HotspotVoucher.DoesNotExist as exc:
        raise VoucherRedemptionError(
            "Voucher code was not found."
        ) from exc

    if voucher.status == "generated":
        try:
            return activate_voucher(
                voucher,
                mac_address,
            )
        except VoucherActivationError as exc:
            raise VoucherRedemptionError(
                str(exc)
            ) from exc

    raise VoucherRedemptionError(
        f"Voucher {voucher.code} cannot be redeemed "
        f"because its status is '{voucher.status}'."
    )
