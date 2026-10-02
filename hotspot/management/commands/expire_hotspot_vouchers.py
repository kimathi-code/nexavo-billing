from django.core.management.base import BaseCommand
from django.utils import timezone

from hotspot.models import HotspotVoucher
from hotspot.services.voucher_service import expire_voucher_if_needed


class Command(BaseCommand):
    help = "Expire active Hotspot vouchers whose expiry time has been reached."

    def handle(self, *args, **options):
        now = timezone.now()

        vouchers = HotspotVoucher.objects.filter(
            status="active",
            expires_at__isnull=False,
            expires_at__lte=now,
        )

        expired_count = 0

        for voucher in vouchers:
            expired = expire_voucher_if_needed(voucher)

            if expired.status == "expired":
                expired_count += 1

        if expired_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Expired {expired_count} hotspot voucher(s)."
                )
            )
        else:
            self.stdout.write(
                "No expired hotspot vouchers found."
            )
