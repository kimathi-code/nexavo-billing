import logging

from django.http import response

import africastalking

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USERNAME = os.getenv(
    "AT_USERNAME"
)

API_KEY = os.getenv(
    "AT_API_KEY"
)
# Initialize Africa's Talking
africastalking.initialize(
    USERNAME,
    API_KEY
)

sms = africastalking.SMS
# Initialize the logger
logger = logging.getLogger("sms")

def send_sms(
    phone_number,
    message,
    sender_id=None
):
    logger.info(
        f"Sending SMS to {phone_number}"
    )

    try:

        if sender_id:

            response = sms.send(
                message,
                [phone_number],
                sender_id
            )

        else:

            response = sms.send(
                message,
                [phone_number]
            )
        logger.info(response)
         
        recipient = (
            response['SMSMessageData']
            ['Recipients'][0]
        )

        return {

            "success": True,

            "status": recipient.get(
                "status"
            ),

            "message_id": recipient.get(
                "messageId"
            ),

            "response": response
        }
         

    except Exception as e:
        logger.exception(e)
        return {

            "success": False,

            "status": "FAILED",

            "message_id": None,

            "error": str(e)
        }