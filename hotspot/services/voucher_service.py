from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from hotspot.models import HotspotPlan, HotspotVoucher


class VoucherServiceError(Exception):
    """Base exception for Hotspot voucher service errors."""


class VoucherActivationError(VoucherServiceError):
    """Raised when a voucher cannot be activated."""


class VoucherAccessError(VoucherServiceError):
    """Raised when a device cannot access a voucher."""


def generate_voucher(plan: HotspotPlan) -> HotspotVoucher:
    """
    Generate a new unused Hotspot voucher for the supplied plan.

    The voucher is created in the 'generated' state.
    It is not activated, bound to a device, or given an expiry time
    until activate_voucher() is called.
    """

    if not isinstance(plan, HotspotPlan):
        raise TypeError("plan must be a HotspotPlan instance.")

    if not plan.active:
        raise ValueError("Cannot generate a voucher for an inactive plan.")

    return HotspotVoucher.objects.create(
        plan=plan,
        status="generated",
    )


def activate_voucher(
    voucher: HotspotVoucher,
    mac_address: str,
) -> HotspotVoucher:
    """
    Activate a generated Hotspot voucher and permanently bind it
    to the first device MAC address for the voucher's active lifetime.

    Activation:
        - locks the voucher row
        - verifies that the voucher is still generated
        - normalizes the MAC address
        - records activation time
        - calculates expiry from the plan duration
        - changes status to active

    The operation is atomic so two simultaneous activation attempts
    cannot both successfully claim the voucher.
    """

    if not isinstance(voucher, HotspotVoucher):
        raise TypeError(
            "voucher must be a HotspotVoucher instance."
        )

    with transaction.atomic():
        locked_voucher = (
            HotspotVoucher.objects
            .select_for_update()
            .select_related("plan")
            .get(pk=voucher.pk)
        )

        if locked_voucher.status != "generated":
            raise VoucherActivationError(
                f"Voucher {locked_voucher.code} cannot be activated "
                f"because its status is '{locked_voucher.status}'."
            )

        if not locked_voucher.plan.active:
            raise VoucherActivationError(
                f"Voucher {locked_voucher.code} belongs to an inactive plan."
            )

        try:
            normalized_mac = HotspotVoucher.normalize_mac(
                mac_address
            )
        except ValueError as exc:
            raise VoucherActivationError(
                str(exc)
            ) from exc

        activated_at = timezone.now()
        expires_at = activated_at + timedelta(
            minutes=locked_voucher.plan.duration_minutes
        )

        locked_voucher.bound_mac = normalized_mac
        locked_voucher.activated_at = activated_at
        locked_voucher.expires_at = expires_at
        locked_voucher.status = "active"

        locked_voucher.save(
            update_fields=[
                "bound_mac",
                "activated_at",
                "expires_at",
                "status",
                "updated_at",
            ]
        )

    return locked_voucher

def expire_voucher_if_needed(
    voucher: HotspotVoucher,
) -> HotspotVoucher:
    """
    Mark an active voucher as expired when its expiry time has been reached.

    Returns the current voucher state.
    """

    if not isinstance(voucher, HotspotVoucher):
        raise TypeError(
            "voucher must be a HotspotVoucher instance."
        )

    with transaction.atomic():
        locked_voucher = (
            HotspotVoucher.objects
            .select_for_update()
            .select_related("plan")
            .get(pk=voucher.pk)
        )

        if locked_voucher.status != "active":
            return locked_voucher

        now = timezone.now()

        if (
            locked_voucher.expires_at is not None
            and now >= locked_voucher.expires_at
        ):
            locked_voucher.status = "expired"

            locked_voucher.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return locked_voucher


def validate_voucher_access(
    voucher: HotspotVoucher,
    mac_address: str,
) -> HotspotVoucher:
    """
    Validate whether a device is currently allowed to use a voucher.

    Access is allowed only when:
        - the voucher is active
        - the voucher has not expired
        - the supplied MAC matches the bound MAC

    Returns the active voucher when access is allowed.
    Raises VoucherAccessError otherwise.
    """

    if not isinstance(voucher, HotspotVoucher):
        raise TypeError(
            "voucher must be a HotspotVoucher instance."
        )

    try:
        normalized_mac = HotspotVoucher.normalize_mac(
            mac_address
        )
    except ValueError as exc:
        raise VoucherAccessError(str(exc)) from exc

    expired = False
    expired_code = None

    with transaction.atomic():
        locked_voucher = (
            HotspotVoucher.objects
            .select_for_update()
            .select_related("plan")
            .get(pk=voucher.pk)
        )

        if locked_voucher.status == "disabled":
            raise VoucherAccessError(
                f"Voucher {locked_voucher.code} is disabled."
            )

        if locked_voucher.status == "generated":
            raise VoucherAccessError(
                f"Voucher {locked_voucher.code} has not been activated."
            )

        if locked_voucher.status == "expired":
            raise VoucherAccessError(
                f"Voucher {locked_voucher.code} has expired."
            )

        now = timezone.now()

        if (
            locked_voucher.expires_at is None
            or now >= locked_voucher.expires_at
        ):
            locked_voucher.status = "expired"

            locked_voucher.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            expired = True
            expired_code = locked_voucher.code

        elif locked_voucher.bound_mac != normalized_mac:
            raise VoucherAccessError(
                f"Device MAC does not match the MAC bound "
                f"to voucher {locked_voucher.code}."
            )
        else:
            return locked_voucher

    if expired:
        raise VoucherAccessError(
            f"Voucher {expired_code} has expired."
        )

def disable_voucher(
    voucher: HotspotVoucher,
) -> HotspotVoucher:
    """
    Disable a voucher.

    A disabled voucher cannot be used or activated again.
    """

    if not isinstance(voucher, HotspotVoucher):
        raise TypeError(
            "voucher must be a HotspotVoucher instance."
        )

    with transaction.atomic():
        locked_voucher = (
            HotspotVoucher.objects
            .select_for_update()
            .get(pk=voucher.pk)
        )

        if locked_voucher.status == "disabled":
            return locked_voucher

        if locked_voucher.status == "expired":
            raise VoucherServiceError(
                f"Expired voucher {locked_voucher.code} "
                "cannot be disabled because it is already expired."
            )

        locked_voucher.status = "disabled"

        locked_voucher.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return locked_voucher
