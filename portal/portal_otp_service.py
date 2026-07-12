from datetime import timedelta

from django.utils import timezone

from django.core.exceptions import ValidationError

from portal.models import PortalActivationOTP

from services.sms_service import send_sms


def send_portal_otp(
    client,
    purpose="activation"
):

    recent_otp = (
        PortalActivationOTP.objects
        .filter(
            client=client,
            purpose=purpose,
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


    PortalActivationOTP.objects.filter(
        client=client,
        purpose=purpose,
        is_used=False
    ).update(
        is_used=True
    )


    otp = PortalActivationOTP.generate(
        client=client,
        purpose=purpose
    )


    message = (
        f"Your Nexavo verification code is {otp.code}. "
        "This code expires in 10 minutes."
    )


    send_sms(
        phone_number=client.phone,
        message=message,
        sender_id="Nexavo"
    )


    return otp



def verify_portal_otp(
    client,
    code,
    purpose="activation"
):

    otp = (
        PortalActivationOTP.objects
        .filter(
            client=client,
            code=code,
            purpose=purpose,
            is_used=False
        )
        .order_by(
            "-created_at"
        )
        .first()
    )


    if not otp:

        raise ValidationError(
            "Invalid verification code."
        )


    if otp.has_expired():

        raise ValidationError(
            "Verification code expired."
        )


    otp.is_used = True


    otp.save(
        update_fields=[
            "is_used"
        ]
    )


    return True

def send_portal_activation_otp(
    client
):

    return send_portal_otp(
        client=client,
        purpose="activation"
    )



def verify_portal_activation_otp(
    client,
    code
):

    return verify_portal_otp(
        client=client,
        code=code,
        purpose="activation"
    )