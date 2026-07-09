from django.core.exceptions import ValidationError
from portal.models import PortalActivationOTP
from services.sms_service import send_sms
from datetime import timedelta
from django.utils import timezone

def send_portal_activation_otp(client):
    # Check if the client has requested an OTP in the last 120 seconds
    recent_otp = (
        PortalActivationOTP.objects
        .filter(
            client=client,
            is_used=False
        )
        .order_by(
            "-created_at"
        )
        .first()
    )


    if recent_otp:

        wait_until = (
            recent_otp.created_at
            + timedelta(seconds=120)
        )

        if timezone.now() < wait_until:

            raise ValidationError(
                "Please wait before requesting another verification code."
            )
    """
    Generate and send customer portal activation OTP.
    """

    PortalActivationOTP.objects.filter(
        client=client,
        is_used=False
    ).update(
        is_used=True
    )

    otp = PortalActivationOTP.generate(
        client=client
    )
    # build the message to be sent to the customer
    message = (
        f"Your Nexavo customer portal activation code is {otp.code}. "
        "This code expires in 10 minutes."
    )

    send_sms(
        phone_number=client.phone,
        message=message,
        sender_id="NEXAVO"
    )

    return otp

# otp verification function
def verify_portal_activation_otp(
    client,
    code
):
    """
    Verify portal activation OTP.
    """

    otp = (
        PortalActivationOTP.objects
        .filter(
            client=client,
            code=code,
            is_used=False
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    if not otp:
        raise ValidationError(
            "Invalid activation code."
        )


    if otp.has_expired():
        raise ValidationError(
            "Activation code expired."
        )


    otp.is_used = True

    otp.save(
        update_fields=[
            "is_used"
        ]
    )

    return True

