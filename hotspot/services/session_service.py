from django.db import transaction
from django.utils import timezone

from hotspot.models import (
    HotspotLocation,
    HotspotSession,
    HotspotVoucher,
)


class SessionServiceError(Exception):
    """Base exception for Hotspot session service errors."""


class SessionStartError(SessionServiceError):
    """Raised when a Hotspot session cannot be started."""


class SessionUpdateError(SessionServiceError):
    """Raised when a Hotspot session cannot be updated."""


def start_session(
    voucher: HotspotVoucher,
    location: HotspotLocation,
    mac_address: str,
    ip_address: str | None = None,
    username: str | None = None,
) -> HotspotSession:
    """
    Start a Hotspot session for an active voucher.

    The supplied MAC address must match the MAC bound to the voucher.
    """

    if not isinstance(voucher, HotspotVoucher):
        raise TypeError(
            "voucher must be a HotspotVoucher instance."
        )

    if not isinstance(location, HotspotLocation):
        raise TypeError(
            "location must be a HotspotLocation instance."
        )

    if not location.active:
        raise SessionStartError(
            f"Hotspot location '{location.name}' is inactive."
        )

    try:
        normalized_mac = HotspotVoucher.normalize_mac(mac_address)
    except ValueError as exc:
        raise SessionStartError(str(exc)) from exc

    expired = False
    expired_code = None

    with transaction.atomic():
        locked_voucher = (
            HotspotVoucher.objects
            .select_for_update()
            .get(pk=voucher.pk)
        )

        if locked_voucher.status != "active":
            raise SessionStartError(
                f"Voucher {locked_voucher.code} cannot start a "
                f"session because its status is "
                f"'{locked_voucher.status}'."
            )

        if locked_voucher.expires_at is None:
            raise SessionStartError(
                f"Voucher {locked_voucher.code} has no expiry time."
            )

        now = timezone.now()

        if now >= locked_voucher.expires_at:
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
            raise SessionStartError(
                "Device MAC does not match the MAC bound "
                f"to voucher {locked_voucher.code}."
            )

        else:
            session = HotspotSession.objects.create(
                voucher=locked_voucher,
                location=location,
                username=username,
                mac_address=normalized_mac,
                ip_address=ip_address,
                started_at=now,
            )

            return session

    if expired:
        raise SessionStartError(
            f"Voucher {expired_code} has expired."
        )


def record_session_usage(
    session: HotspotSession,
    bytes_in: int,
    bytes_out: int,
) -> HotspotSession:
    """
    Record cumulative network usage for a Hotspot session.

    bytes_in and bytes_out represent the current cumulative
    counters reported by the network device.
    """

    if not isinstance(session, HotspotSession):
        raise TypeError(
            "session must be a HotspotSession instance."
        )

    if bytes_in < 0 or bytes_out < 0:
        raise SessionUpdateError(
            "Usage counters cannot be negative."
        )

    if session.ended_at is not None:
        raise SessionUpdateError(
            f"Session {session.pk} has already ended."
        )

    with transaction.atomic():
        locked_session = (
            HotspotSession.objects
            .select_for_update()
            .get(pk=session.pk)
        )

        if locked_session.ended_at is not None:
            raise SessionUpdateError(
                f"Session {locked_session.pk} has already ended."
            )

        locked_session.bytes_in = bytes_in
        locked_session.bytes_out = bytes_out

        locked_session.save(
            update_fields=[
                "bytes_in",
                "bytes_out",
            ]
        )

    return locked_session


def end_session(
    session: HotspotSession,
    bytes_in: int | None = None,
    bytes_out: int | None = None,
) -> HotspotSession:
    """
    End an active Hotspot session.

    Optional final byte counters can be supplied when the network
    device sends its final accounting update.
    """

    if not isinstance(session, HotspotSession):
        raise TypeError(
            "session must be a HotspotSession instance."
        )

    if bytes_in is not None and bytes_in < 0:
        raise SessionUpdateError(
            "bytes_in cannot be negative."
        )

    if bytes_out is not None and bytes_out < 0:
        raise SessionUpdateError(
            "bytes_out cannot be negative."
        )

    with transaction.atomic():
        locked_session = (
            HotspotSession.objects
            .select_for_update()
            .get(pk=session.pk)
        )

        if locked_session.ended_at is not None:
            raise SessionUpdateError(
                f"Session {locked_session.pk} has already ended."
            )

        if bytes_in is not None:
            locked_session.bytes_in = bytes_in

        if bytes_out is not None:
            locked_session.bytes_out = bytes_out

        locked_session.ended_at = timezone.now()

        locked_session.save(
            update_fields=[
                "bytes_in",
                "bytes_out",
                "ended_at",
            ]
        )

    return locked_session
