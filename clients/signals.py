import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from clients.models import (
    Payment,
    NotificationLog,
)

from services.sms_service import (
    send_sms,
)

from services.payment_notification_service import (
    build_payment_confirmation_message,
)

from services.payment_processing_service import (
    process_payment,
)


logger = logging.getLogger("billing")


@receiver(post_save, sender=Payment)
def process_payment_signal(
    sender,
    instance,
    created,
    **kwargs
):

    # Only process newly created payments
    if not created:
        return

    # ---------------------------------------------------------
    # 1. Process payment
    # ---------------------------------------------------------

    processing_result = process_payment(instance)

    logger.info(
        "Payment processing result for %s: %s",
        instance.transaction_code,
        processing_result,
    )

    payment_id = instance.pk

    # ---------------------------------------------------------
    # 2. Send notification after transaction commit
    # ---------------------------------------------------------

    def _send_notification_post_commit():

        try:

            # Reload fresh database state
            payment = (
                Payment.objects
                .select_related("client")
                .get(pk=payment_id)
            )

            client = payment.client

            message = (
                build_payment_confirmation_message(
                    payment
                )
            )

            sms_result = send_sms(

                client.phone,

                message,

                sender_id="NEXAVO",
            )

            NotificationLog.objects.create(

                client=client,

                notification_type=(
                    "payment_confirmation"
                ),

                message=message,

                phone_number=client.phone,

                delivery_status=sms_result.get(
                    "status"
                ),

                gateway_message_id=sms_result.get(
                    "message_id"
                ),

                gateway_response=str(
                    sms_result
                ),
            )

            logger.info(
                "Payment confirmation SMS sent "
                "for payment %s.",
                payment.transaction_code,
            )

            print(
                f"Payment processed for "
                f"{client.name}"
            )

        except Exception:

            logger.exception(
                "Failed to dispatch SMS confirmation "
                "for payment %s.",
                instance.transaction_code,
            )

    transaction.on_commit(
        _send_notification_post_commit
    )