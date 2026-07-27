import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from clients.models import Payment, NotificationLog
from services.sms_service import (
    send_sms
)

from services.payment_notification_service import (
    build_payment_confirmation_message
)

from services.billing_service import (
    process_client_renewal
)

logger = logging.getLogger("billing")

@receiver(post_save, sender=Payment)
def process_payment(
    sender,
    instance,
    created,
    **kwargs
):

    if not created:
        return

    client = instance.client

    # ADD FUNDS TO WALLET
    client.wallet_balance += instance.amount

    client.save()

    # PROCESS AUTOMATIC RENEWAL
    renewal_result = process_client_renewal(client)

    logger.info(
        f"Automatic renewal result for "
        f"{client.account_number}: "
        f"{renewal_result['message']}"
    )

    message = (
        build_payment_confirmation_message(
            instance
        )
    )

    sms_result = send_sms(

        client.phone,

        message,

        sender_id="NEXAVO"
    )

    NotificationLog.objects.create(

        client=client,

        notification_type='payment_confirmation',

        message=message,

	    phone_number=client.phone,

        delivery_status=sms_result.get(
            "status"
        ),

        gateway_message_id=sms_result.get(
            "message_id"
        ),

        gateway_response=str(sms_result)
    )

    # PAYMENT STATUS
    if client.wallet_balance > 0:

        instance.status = 'credit'

    else:

        instance.status = 'completed'

    instance.save()

    print(
        f"Wallet updated for "
        f"{client.name}"
    )

