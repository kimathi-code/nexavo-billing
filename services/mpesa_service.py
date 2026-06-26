import os
import base64
import requests
import logging
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from clients.models import (
    Client,
    Payment,
    MpesaTransaction,
    StkPushRequest
)

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("mpesa")


class MpesaService:

    def __init__(self):

        self.consumer_key = os.getenv(
            "MPESA_CONSUMER_KEY"
        )

        self.consumer_secret = os.getenv(
            "MPESA_CONSUMER_SECRET"
        )

        self.shortcode = os.getenv(
            "MPESA_SHORTCODE"
        )

        self.passkey = os.getenv(
            "MPESA_PASSKEY"
        )

        self.callback_url = os.getenv(
            "MPESA_CALLBACK_URL"
        )
        self.stk_callback_url = os.getenv(
            "STK_CALLBACK_URL"
        )

    def get_access_token(self):

        url = (
            "https://sandbox.safaricom.co.ke/"
            "oauth/v1/generate"
            "?grant_type=client_credentials"
        )

        response = requests.get(
            url,
            auth=(
                self.consumer_key,
                self.consumer_secret
            )
        )

        response.raise_for_status()

        return response.json()[
            "access_token"
        ]
    
    # helper function to format phone number to Daraja format
    def format_phone_number(self, phone):

        phone = phone.strip()

        if phone.startswith("+254"):
            return phone[1:]

        if phone.startswith("07"):
            return "254" + phone[1:]

        if phone.startswith("7"):
            return "254" + phone

        return phone

    #INTIATE STK PUSH

    def initiate_stk_push(
        
        self,

        client,

        amount

    ):
        logger.info(
            f"Initiating STK Push | "
            f"Account: {client.account_number} | "
            f"Amount: {amount}"
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )

        # Generate password and encode it in base64
        password = base64.b64encode(
            (
                self.shortcode
                + self.passkey
                + timestamp
            ).encode()
        ).decode()

        access_token = self.get_access_token()

        headers = {

            "Authorization": f"Bearer {access_token}",

            "Content-Type": "application/json"
        }

        # Convert stored phone number into Daraja format.
        phone = self.format_phone_number(client.phone)

        payload = {

            "BusinessShortCode": self.shortcode,

            "Password": password,

            "Timestamp": timestamp,

            "TransactionType": "CustomerPayBillOnline",

            "Amount": int(amount),

            "PartyA": phone,

            "PartyB": self.shortcode,

            "PhoneNumber": phone,

            "CallBackURL": self.stk_callback_url,

            "AccountReference": client.account_number,

            "TransactionDesc": "Internet Subscription"
        }


        # POST request
        try:
            logger.info(
                f"STK Payload: {payload}"
            )
            response = requests.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()
            response_data = response.json()
        except requests.RequestException:

            logger.exception(
                "Unexpected error while initiating STK Push"
            )

            try:
                error_response = response.json()
            except Exception:
                error_response = response.text

            logger.error(
                f"Daraja Error Response: {error_response}"
            )

            return {
                "success": False,
                "error": error_response
            }


        # Safely extract variables immediately after successful JSON parsing
        response_code = str(response_data.get("ResponseCode", "-1")) # Default to "-1" if completely missing
        checkout_id = response_data.get("CheckoutRequestID")
        response_desc = response_data.get("ResponseDescription", "No description provided")

        # Check if Safaricom accepted the request successfully
        if response_code == "0":

            logger.info(
                f"Daraja Response: {response_data}"
            )

            # create the pending database record
            stk_request = StkPushRequest.objects.create(
                merchant_request_id=response_data.get("MerchantRequestID"),
                checkout_request_id=response_data.get("CheckoutRequestID"),
                account_reference=client.account_number,
                phone_number=client.phone,
                amount=amount,
                response_code=response_data.get("ResponseCode"),
                response_description=response_data.get("ResponseDescription"),
                raw_response=response_data,
                status="pending"
            )

            return {
                "success": True,
                "response": response_data
            }
        else:
            # Safaricom hit back with an API level error code 
            logger.warning(
                f"STK Push Rejected by Safaricom API | " 
                f"Code: {response_code} | "
                f"Desc: {response_desc}"
            )

            stk_request = StkPushRequest.objects.create(
                merchant_request_id=response_data.get("MerchantRequestID"),
                checkout_request_id=checkout_id,
                account_reference=client.account_number,
                phone_number=client.phone,
                amount=amount,
                response_code=response_code,
                response_description=response_desc,
                raw_response=response_data,
                status="failed"
            )

            return {
                "success": False,
                "error": response_desc,
                "stk_request": stk_request
            }

#PROCESS PAYMENT TRANSACTION
def process_payment_transaction(
    receipt_number,
    account_reference,
    phone_number,
    amount,
    payload=None
):
    amount = Decimal(str(amount))

    # Prevent duplicates
    if MpesaTransaction.objects.filter(
        receipt_number=receipt_number
    ).exists():

        return {
            "success": False,
            "message": "Transaction already exists"
        }

    # Store raw M-Pesa transaction
    transaction = MpesaTransaction.objects.create(

        receipt_number=receipt_number,

        account_reference=account_reference,

        phone_number=phone_number,

        amount=amount,

        raw_payload=payload,

        processing_status='pending'
    )

    try:

        client = Client.objects.get(
            account_number=account_reference
        )

    except Client.DoesNotExist:

        transaction.processing_status = 'failed'
        transaction.processed_at = (
            timezone.now()
        )

        transaction.save()

        return {

            "success": False,

            "message": (
                f"Account "
                f"{account_reference} "
                f"not found"
            )
        }

    # Create Payment record
    payment = Payment.objects.create(

        client=client,

        amount=amount,

        transaction_code=receipt_number,

        account_reference=account_reference,

        payment_method='mpesa'
    )

    transaction.processing_status = 'processed'

    transaction.processed_at = (
        timezone.now()
    )

    transaction.save()

    return {

        "success": True,

        "client": client.name,

        "payment_id": payment.id,

        "transaction_id": transaction.id
    }

#Payload Parser
def extract_mpesa_data(payload):

    try:

        receipt_number = payload.get(
            "TransID"
        )

        account_reference = payload.get(
            "BillRefNumber"
        )

        phone_number = payload.get(
            "MSISDN"
        )

        amount = payload.get(
            "TransAmount"
        )

        return {

            "receipt_number": receipt_number,

            "account_reference": account_reference,

            "phone_number": str(
                phone_number
            ),

            "amount": amount
        }

    except Exception as e:

        print(
            f"Failed to parse payload: {e}"
        )

        return None
    
