from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from services.payment_matching_service import match_payment_reference
from clients.models import Client
from hotspot.models import (
    HotspotLocation,
    HotspotPlan,
    HotspotPurchase,
    HotspotSession,
    HotspotVoucher,
)

from hotspot.models import HotspotPlan, HotspotVoucher
from hotspot.services.voucher_service import (
    VoucherActivationError,
    VoucherAccessError,
    generate_voucher,
    activate_voucher,
    validate_voucher_access,
    expire_voucher_if_needed,
    disable_voucher,
)

from hotspot.services.purchase_service import (
    PurchaseValidationError,
    create_hotspot_purchase,
    confirm_hotspot_purchase,
)

from hotspot.services.redemption_service import (
    VoucherRedemptionError,
    redeem_voucher,
)


from hotspot.models import (
    HotspotLocation,
    HotspotPlan,
    HotspotSession,
    HotspotVoucher,
)

from hotspot.services.session_service import (
    SessionStartError,
    SessionUpdateError,
    start_session,
    record_session_usage,
    end_session,
)

class HotspotVoucherServiceTests(TestCase):
    def setUp(self):
        self.plan = HotspotPlan.objects.create(
            name="Test 2 Hours",
            price=10,
            duration_minutes=120,
            download_speed_kbps=5000,
            upload_speed_kbps=2000,
            simultaneous_devices=1,
        )

    def test_generate_voucher(self):
        voucher = generate_voucher(self.plan)

        self.assertIsInstance(voucher, HotspotVoucher)
        self.assertTrue(voucher.code.startswith("NXV-HS-"))
        self.assertEqual(voucher.status, "generated")
        self.assertIsNone(voucher.activated_at)
        self.assertIsNone(voucher.expires_at)
        self.assertIsNone(voucher.bound_mac)
        self.assertEqual(voucher.plan, self.plan)

    def test_generate_voucher_creates_unique_codes(self):
        voucher_one = generate_voucher(self.plan)
        voucher_two = generate_voucher(self.plan)

        self.assertNotEqual(
            voucher_one.code,
            voucher_two.code,
        )

    def test_activate_voucher(self):
        voucher = generate_voucher(self.plan)

        activated = activate_voucher(
            voucher,
            "aa-bb-cc-dd-ee-ff",
        )

        self.assertEqual(activated.status, "active")
        self.assertEqual(
            activated.bound_mac,
            "AA:BB:CC:DD:EE:FF",
        )
        self.assertIsNotNone(activated.activated_at)
        self.assertIsNotNone(activated.expires_at)

        duration = (
            activated.expires_at
            - activated.activated_at
        )

        self.assertEqual(
            duration,
            timedelta(minutes=120),
        )

    def test_second_activation_is_rejected(self):
        voucher = generate_voucher(self.plan)

        activated = activate_voucher(
            voucher,
            "AA:BB:CC:DD:EE:FF",
        )

        with self.assertRaises(VoucherActivationError):
            activate_voucher(
                activated,
                "11:22:33:44:55:66",
            )

    def test_correct_mac_is_allowed(self):
        voucher = generate_voucher(self.plan)

        activated = activate_voucher(
            voucher,
            "AA:BB:CC:DD:EE:FF",
        )

        result = validate_voucher_access(
            activated,
            "AA:BB:CC:DD:EE:FF",
        )

        self.assertEqual(result.pk, voucher.pk)
        self.assertEqual(result.status, "active")

    def test_different_mac_is_rejected(self):
        voucher = generate_voucher(self.plan)

        activated = activate_voucher(
            voucher,
            "AA:BB:CC:DD:EE:FF",
        )

        with self.assertRaises(VoucherAccessError):
            validate_voucher_access(
                activated,
                "11:22:33:44:55:66",
            )

    def test_equivalent_mac_format_is_allowed(self):
        voucher = generate_voucher(self.plan)

        activated = activate_voucher(
            voucher,
            "AA:BB:CC:DD:EE:FF",
        )

        result = validate_voucher_access(
            activated,
            "aa-bb-cc-dd-ee-ff",
        )

        self.assertEqual(result.pk, voucher.pk)
        self.assertEqual(result.status, "active")

    def test_generated_voucher_is_rejected(self):
        voucher = generate_voucher(self.plan)

        with self.assertRaises(VoucherAccessError):
            validate_voucher_access(
                voucher,
                "AA:BB:CC:DD:EE:FF",
            )

    def test_disabled_voucher_is_rejected(self):
        voucher = generate_voucher(self.plan)

        disabled = disable_voucher(voucher)

        self.assertEqual(
            disabled.status,
            "disabled",
        )

        with self.assertRaises(VoucherAccessError):
            validate_voucher_access(
                disabled,
                "AA:BB:CC:DD:EE:FF",
            )

    def test_expired_voucher_is_rejected(self):
        voucher = generate_voucher(self.plan)

        activated = activate_voucher(
            voucher,
            "AA:BB:CC:DD:EE:FF",
        )

        activated.expires_at = timezone.now() - timedelta(
            minutes=1
        )
        activated.save(
            update_fields=[
                "expires_at",
                "updated_at",
            ]
        )

        with self.assertRaises(VoucherAccessError):
            validate_voucher_access(
                activated,
                "AA:BB:CC:DD:EE:FF",
            )

        activated.refresh_from_db()

        self.assertEqual(
            activated.status,
            "expired",
        )

    def test_expire_voucher_if_needed(self):
        voucher = generate_voucher(self.plan)

        activated = activate_voucher(
            voucher,
            "AA:BB:CC:DD:EE:FF",
        )

        activated.expires_at = timezone.now() - timedelta(
            minutes=1
        )
        activated.save(
            update_fields=[
                "expires_at",
                "updated_at",
            ]
        )

        expired = expire_voucher_if_needed(activated)

        self.assertEqual(
            expired.status,
            "expired",
        )

        expired.refresh_from_db()

        self.assertEqual(
            expired.status,
            "expired",
        )


# purchase tests
class HotspotPurchaseServiceTests(TestCase):

    def setUp(self):
        self.plan = HotspotPlan.objects.create(
            name="Test 2 Hours",
            price=10,
            duration_minutes=120,
            download_speed_kbps=5000,
            upload_speed_kbps=2000,
            simultaneous_devices=1,
        )

    def test_create_hotspot_purchase(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254712345678",
        )

        self.assertEqual(purchase.plan, self.plan)
        self.assertEqual(purchase.amount, self.plan.price)
        self.assertEqual(purchase.payment_method, "mpesa")
        self.assertEqual(
            purchase.phone_number,
            "+254712345678",
        )
        self.assertEqual(purchase.status, "pending")
        self.assertIsNone(purchase.voucher)
        self.assertIsNone(purchase.transaction_reference)
        self.assertIsNone(purchase.paid_at)

    def test_pending_purchase_has_no_voucher(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254712345678",
        )

        self.assertIsNone(purchase.voucher)

    def test_confirm_purchase_issues_voucher(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254712345678",
        )

        confirmed = confirm_hotspot_purchase(
            purchase,
            "TEST-MPESA-001",
        )

        confirmed.refresh_from_db()

        self.assertEqual(confirmed.status, "paid")
        self.assertEqual(
            confirmed.transaction_reference,
            "TEST-MPESA-001",
        )
        self.assertIsNotNone(confirmed.paid_at)
        self.assertIsNotNone(confirmed.voucher)

        self.assertEqual(
            confirmed.voucher.plan,
            self.plan,
        )

        self.assertEqual(
            confirmed.voucher.status,
            "generated",
        )

    def test_confirm_purchase_is_idempotent(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254712345678",
        )

        first = confirm_hotspot_purchase(
            purchase,
            "TEST-MPESA-002",
        )

        voucher_id = first.voucher_id

        second = confirm_hotspot_purchase(
            purchase,
            "TEST-MPESA-002",
        )

        self.assertEqual(
            second.voucher_id,
            voucher_id,
        )

        self.assertEqual(
            HotspotVoucher.objects.count(),
            1,
        )

    def test_inactive_plan_cannot_create_purchase(self):
        self.plan.active = False
        self.plan.save(update_fields=["active"])

        with self.assertRaises(PurchaseValidationError):
            create_hotspot_purchase(
                plan=self.plan,
                payment_method="mpesa",
                phone_number="+254712345678",
            )

    def test_mpesa_purchase_requires_phone_number(self):
        with self.assertRaises(PurchaseValidationError):
            create_hotspot_purchase(
                plan=self.plan,
                payment_method="mpesa",
            )

    def test_invalid_payment_method_is_rejected(self):
        with self.assertRaises(PurchaseValidationError):
            create_hotspot_purchase(
                plan=self.plan,
                payment_method="bank",
                phone_number="+254712345678",
            )

    def test_payment_reference_is_generated(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254700000000",
        )

    def test_payment_reference_collision_is_retried(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254700000005",
        )

        existing_reference = purchase.payment_reference

        references = iter([
            existing_reference,
            "HS-IJKLMNOP",
        ])

        with patch.object(
            HotspotPurchase,
            "generate_payment_reference",
            side_effect=lambda: next(references),
        ):
            second_purchase = HotspotPurchase(
                plan=self.plan,
                amount=self.plan.price,
                payment_method="mpesa",
                phone_number="+254700000006",
            )
            second_purchase.save()

        self.assertEqual(
            second_purchase.payment_reference,
            "HS-IJKLMNOP",
        )

        self.assertNotEqual(
            second_purchase.payment_reference,
            existing_reference,
        )

    def test_payment_references_are_unique(self):
        purchase_one = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254700000001",
        )

        purchase_two = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254700000002",
        )

        self.assertNotEqual(
            purchase_one.payment_reference,
            purchase_two.payment_reference,
        )

    def test_payment_reference_does_not_change_when_purchase_is_saved(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254700000003",
        )

        original_reference = purchase.payment_reference

        purchase.phone_number = "+254711111111"
        purchase.save()

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.payment_reference,
            original_reference,
        )

    def test_transaction_reference_is_independent_of_payment_reference(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254700000004",
        )

        payment_reference = purchase.payment_reference

        self.assertIsNone(purchase.transaction_reference)

        purchase.transaction_reference = "QABC123XYZ"
        purchase.save()

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.payment_reference,
            payment_reference,
        )
        self.assertEqual(
            purchase.transaction_reference,
            "QABC123XYZ",
        )

class PaymentMatchingServiceTests(TestCase):

    def setUp(self):
        self.plan = HotspotPlan.objects.create(
            name="Test 2 Hours",
            price=10,
            duration_minutes=120,
            download_speed_kbps=5000,
            upload_speed_kbps=2000,
            simultaneous_devices=1,
        )

        self.client = Client.objects.create(
            name="Test Client",
            phone="+254712345678",
            email="testclient@example.com",
            account_number="NXV-1001",
            location="Test Location",
        )

    def test_client_payment_reference_matches_client(self):
        result = match_payment_reference("NXV-1001")

        self.assertTrue(result.matched)
        self.assertEqual(result.payment_type, "client")
        self.assertEqual(result.client, self.client)
        self.assertIsNone(result.hotspot_purchase)

    def test_hotspot_payment_reference_matches_purchase(self):
        purchase = create_hotspot_purchase(
            plan=self.plan,
            payment_method="mpesa",
            phone_number="+254712345679",
        )

        result = match_payment_reference(
            purchase.payment_reference
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.payment_type, "hotspot")
        self.assertEqual(result.hotspot_purchase, purchase)
        self.assertIsNone(result.client)

    def test_unknown_payment_reference_is_unmatched(self):
        result = match_payment_reference("UNKNOWN-12345")

        self.assertFalse(result.matched)
        self.assertIsNone(result.payment_type)
        self.assertIsNone(result.client)
        self.assertIsNone(result.hotspot_purchase)

    def test_payment_reference_is_normalized(self):
        result = match_payment_reference("  nxv-1001  ")

        self.assertTrue(result.matched)
        self.assertEqual(result.payment_type, "client")
        self.assertEqual(result.client, self.client)

    def test_empty_payment_reference_is_unmatched(self):
        result = match_payment_reference("")

        self.assertFalse(result.matched)
        self.assertIsNone(result.payment_type)
        self.assertIsNone(result.client)
        self.assertIsNone(result.hotspot_purchase)

class HotspotVoucherRedemptionTests(TestCase):

    def setUp(self):
        self.plan = HotspotPlan.objects.create(
            name="Test 2 Hours",
            price=10,
            duration_minutes=120,
            download_speed_kbps=5000,
            upload_speed_kbps=2000,
            simultaneous_devices=1,
        )

    def test_redeem_generated_voucher(self):
        voucher = generate_voucher(self.plan)

        redeemed = redeem_voucher(
            voucher.code,
            "AA:BB:CC:DD:EE:FF",
        )

        self.assertEqual(
            redeemed.pk,
            voucher.pk,
        )
        self.assertEqual(
            redeemed.status,
            "active",
        )
        self.assertEqual(
            redeemed.bound_mac,
            "AA:BB:CC:DD:EE:FF",
        )
        self.assertIsNotNone(
            redeemed.activated_at,
        )
        self.assertIsNotNone(
            redeemed.expires_at,
        )

    def test_redeem_unknown_voucher(self):
        with self.assertRaises(VoucherRedemptionError):
            redeem_voucher(
                "NXV-HS-NOTFOUND",
                "AA:BB:CC:DD:EE:FF",
            )

    def test_redeem_active_voucher_again_is_rejected(self):
        voucher = generate_voucher(self.plan)

        redeem_voucher(
            voucher.code,
            "AA:BB:CC:DD:EE:FF",
        )

        with self.assertRaises(VoucherRedemptionError):
            redeem_voucher(
                voucher.code,
                "AA:BB:CC:DD:EE:FF",
            )

    def test_redeem_voucher_with_invalid_mac(self):
        voucher = generate_voucher(self.plan)

        with self.assertRaises(VoucherRedemptionError):
            redeem_voucher(
                voucher.code,
                "INVALID-MAC",
            )

    def test_redeem_voucher_binds_first_device(self):
        voucher = generate_voucher(self.plan)

        redeemed = redeem_voucher(
            voucher.code,
            "AA:BB:CC:DD:EE:FF",
        )

        self.assertEqual(
            redeemed.bound_mac,
            "AA:BB:CC:DD:EE:FF",
        )

        redeemed.refresh_from_db()

        self.assertEqual(
            redeemed.bound_mac,
            "AA:BB:CC:DD:EE:FF",
        )


class HotspotSessionServiceTests(TestCase):

    def setUp(self):
        self.plan = HotspotPlan.objects.create(
            name="Test 2 Hours",
            price=10,
            duration_minutes=120,
            download_speed_kbps=5000,
            upload_speed_kbps=2000,
            simultaneous_devices=1,
        )

        self.location = HotspotLocation.objects.create(
            name="Test Hotspot",
            address="Test Address",
        )

        voucher = generate_voucher(self.plan)

        self.voucher = activate_voucher(
            voucher,
            "AA:BB:CC:DD:EE:FF",
        )

    def test_start_session(self):
        session = start_session(
            voucher=self.voucher,
            location=self.location,
            mac_address="AA:BB:CC:DD:EE:FF",
            ip_address="10.20.30.40",
            username="NXV-HS-TEST",
        )

        self.assertEqual(
            session.voucher,
            self.voucher,
        )
        self.assertEqual(
            session.location,
            self.location,
        )
        self.assertEqual(
            session.mac_address,
            "AA:BB:CC:DD:EE:FF",
        )
        self.assertEqual(
            session.ip_address,
            "10.20.30.40",
        )
        self.assertEqual(
            session.username,
            "NXV-HS-TEST",
        )
        self.assertIsNotNone(
            session.started_at,
        )
        self.assertIsNone(
            session.ended_at,
        )
        self.assertEqual(
            session.bytes_in,
            0,
        )
        self.assertEqual(
            session.bytes_out,
            0,
        )

    def test_start_session_with_wrong_mac_is_rejected(self):
        with self.assertRaises(SessionStartError):
            start_session(
                voucher=self.voucher,
                location=self.location,
                mac_address="11:22:33:44:55:66",
            )

        self.assertEqual(
            HotspotSession.objects.count(),
            0,
        )

    def test_start_session_at_inactive_location_is_rejected(self):
        self.location.active = False
        self.location.save(update_fields=["active"])

        with self.assertRaises(SessionStartError):
            start_session(
                voucher=self.voucher,
                location=self.location,
                mac_address="AA:BB:CC:DD:EE:FF",
            )

        self.assertEqual(
            HotspotSession.objects.count(),
            0,
        )

    def test_record_session_usage(self):
        session = start_session(
            voucher=self.voucher,
            location=self.location,
            mac_address="AA:BB:CC:DD:EE:FF",
        )

        updated = record_session_usage(
            session,
            bytes_in=5000,
            bytes_out=12000,
        )

        self.assertEqual(
            updated.bytes_in,
            5000,
        )
        self.assertEqual(
            updated.bytes_out,
            12000,
        )

    def test_negative_usage_is_rejected(self):
        session = start_session(
            voucher=self.voucher,
            location=self.location,
            mac_address="AA:BB:CC:DD:EE:FF",
        )

        with self.assertRaises(SessionUpdateError):
            record_session_usage(
                session,
                bytes_in=-1,
                bytes_out=100,
            )

    def test_end_session(self):
        session = start_session(
            voucher=self.voucher,
            location=self.location,
            mac_address="AA:BB:CC:DD:EE:FF",
        )

        ended = end_session(
            session,
            bytes_in=8000,
            bytes_out=16000,
        )

        self.assertIsNotNone(
            ended.ended_at,
        )
        self.assertEqual(
            ended.bytes_in,
            8000,
        )
        self.assertEqual(
            ended.bytes_out,
            16000,
        )

    def test_usage_after_session_has_ended_is_rejected(self):
        session = start_session(
            voucher=self.voucher,
            location=self.location,
            mac_address="AA:BB:CC:DD:EE:FF",
        )

        end_session(
            session,
            bytes_in=1000,
            bytes_out=2000,
        )

        with self.assertRaises(SessionUpdateError):
            record_session_usage(
                session,
                bytes_in=5000,
                bytes_out=6000,
            )

    def test_session_cannot_be_ended_twice(self):
        session = start_session(
            voucher=self.voucher,
            location=self.location,
            mac_address="AA:BB:CC:DD:EE:FF",
        )

        end_session(session)

        with self.assertRaises(SessionUpdateError):
            end_session(session)

    def test_expired_voucher_is_marked_expired_when_session_start_is_attempted(self):
        voucher = self.voucher

        voucher.expires_at = timezone.now() - timedelta(minutes=1)
        voucher.save(
            update_fields=[
                "expires_at",
                "updated_at",
            ]
        )

        with self.assertRaises(SessionStartError):
            start_session(
                voucher=voucher,
                location=self.location,
                mac_address="AA:BB:CC:DD:EE:FF",
            )

        voucher.refresh_from_db()

        self.assertEqual(
            voucher.status,
            "expired",
        )

        self.assertEqual(
            HotspotSession.objects.count(),
            0,
        )



