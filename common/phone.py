"""
Shared phone utilities for the Nexavo project.

These helpers normalize and validate Kenyan
phone numbers for use across all services,
including M-Pesa, SMS, customer portal,
and future APIs.
"""


def normalize_phone_number(phone):
    """
    Normalize a Kenyan phone number into
    Daraja format (2547XXXXXXXX).

    Accepted formats:

    +2547XXXXXXXX
    2547XXXXXXXX
    07XXXXXXXX
    7XXXXXXXX
    """

    if not phone:

        return None

    phone = (
        phone
        .strip()
        .replace(" ", "")
    )

    if phone.startswith("+254"):

        return phone[1:]

    if phone.startswith("254"):

        return phone

    if phone.startswith("07"):

        return "254" + phone[1:]

    if phone.startswith("7"):

        return "254" + phone

    return phone


def is_valid_phone_number(phone):
    """
    Validate a normalized Kenyan phone number.

    Expected format:

    2547XXXXXXXX
    """

    if not phone:

        return False

    return (

        phone.startswith("2547")

        and

        len(phone) == 12

        and

        phone.isdigit()

    )