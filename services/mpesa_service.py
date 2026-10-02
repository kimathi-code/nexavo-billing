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
from common.phone import (
    normalize_phone_number,
)

from services.payment_matching_service import (
    match_payment_reference,
)

from hotspot.services.purchase_service import (
    confirm_hotspot_purchase,
    PurchaseServiceError,
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
    
    
    #INTIATE STK PUSH

    def initiate_stk_push(
        
        self,

        client,

        amount,

        override_phone=None

    ):

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
        # Use override phone if provided, otherwise use the client's stored phone number.
        payment_phone = (
            override_phone
            or client.phone
        )

        phone = normalize_phone_number(
            payment_phone
        )

        logger.info(
            "Initiating STK Push | "
            "Account: %s | "
            "Amount: %s | "
            "Phone: %s",
            client.account_number,
            amount,
            payment_phone,
        )

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
                "STK Payload: %s",
                payload
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
                "Daraja Error Response: %s",
                error_response
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
                "Daraja Response: %s",
                response_data
            )

            # create the pending database record
            stk_request = StkPushRequest.objects.create(
                merchant_request_id=response_data.get("MerchantRequestID"),
                checkout_request_id=response_data.get("CheckoutRequestID"),
                account_reference=client.account_number,
                phone_number=payment_phone,
                amount=amount,
                response_code=response_data.get("ResponseCode"),
                response_description=response_data.get("ResponseDescription"),
                raw_response=response_data,
                status="pending"
            )

            return {
                "success": True,
                "response": response_data,
                "stk_request": stk_request,
            }
        else:
            # Safaricom hit back with an API level error code 
            logger.warning(
                "STK Push rejected by Safaricom API | " 
                "Code: %s | "
                "Description: %s",
                response_code,
                response_desc
            )

            stk_request = StkPushRequest.objects.create(
                merchant_request_id=response_data.get("MerchantRequestID"),
                checkout_request_id=checkout_id,
                account_reference=client.account_number,
                phone_number=payment_phone,
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

    # Prevent duplicate M-Pesa transactions
    if MpesaTransaction.objects.filter(
        receipt_number=receipt_number
    ).exists():

        return {
            "success": False,
            "message": "Transaction already exists"
        }

    # Store raw M-Pesa transaction first
    mpesa_transaction = MpesaTransaction.objects.create(
        receipt_number=receipt_number,
        account_reference=account_reference,
        phone_number=phone_number,
        amount=amount,
        raw_payload=payload,
        processing_status="pending"
    )

    # Determine which Nexavo business domain owns the payment
    match = match_payment_reference(
        account_reference
    )

    # ---------------------------------------------------------
    # Unknown payment reference
    # ---------------------------------------------------------

    if not match.matched:

        mpesa_transaction.processing_status = "failed"
        mpesa_transaction.processed_at = timezone.now()
        mpesa_transaction.save(
            update_fields=[
                "processing_status",
                "processed_at",
            ]
        )

        return {
            "success": False,
            "message": match.message,
            "transaction_id": mpesa_transaction.id,
        }

    # ---------------------------------------------------------
    # Registered customer payment
    # ---------------------------------------------------------

    if match.payment_type == "client":

        client = match.client

        payment = Payment.objects.create(
            client=client,
            amount=amount,
            transaction_code=receipt_number,
            account_reference=account_reference,
            payment_method="mpesa"
        )

        mpesa_transaction.processing_status = "processed"
        mpesa_transaction.processed_at = timezone.now()
        mpesa_transaction.save(
            update_fields=[
                "processing_status",
                "processed_at",
            ]
        )

        return {
            "success": True,
            "payment_type": "client",
            "client": client.name,
            "payment_id": payment.id,
            "transaction_id": mpesa_transaction.id,
        }

    # ---------------------------------------------------------
    # Hotspot purchase
    # ---------------------------------------------------------

    if match.payment_type == "hotspot":

        purchase = match.hotspot_purchase

        # Verify that the M-Pesa payment matches
        # the amount of the selected Hotspot plan.
        if amount != purchase.amount:

            mpesa_transaction.processing_status = "failed"
            mpesa_transaction.processed_at = timezone.now()
            mpesa_transaction.save(
                update_fields=[
                    "processing_status",
                    "processed_at",
                ]
            )

            return {
                "success": False,
                "payment_type": "hotspot",
                "message": (
                    "M-Pesa amount does not match "
                    "the selected Hotspot plan."
                ),
                "transaction_id": mpesa_transaction.id,
                "purchase_id": purchase.id,
            }

        try:
            purchase = confirm_hotspot_purchase(
                purchase=purchase,
                transaction_reference=receipt_number,
            )

        except PurchaseServiceError as exc:

            mpesa_transaction.processing_status = "failed"
            mpesa_transaction.processed_at = timezone.now()
            mpesa_transaction.save(
                update_fields=[
                    "processing_status",
                    "processed_at",
                ]
            )

            return {
                "success": False,
                "payment_type": "hotspot",
                "message": str(exc),
                "transaction_id": mpesa_transaction.id,
                "purchase_id": purchase.id,
            }

        mpesa_transaction.processing_status = "processed"
        mpesa_transaction.processed_at = timezone.now()
        mpesa_transaction.save(
            update_fields=[
                "processing_status",
                "processed_at",
            ]
        )

        return {
            "success": True,
            "payment_type": "hotspot",
            "purchase_id": purchase.id,
            "voucher_id": purchase.voucher_id,
            "transaction_id": mpesa_transaction.id,
        }

    # ---------------------------------------------------------
    # Defensive fallback
    # ---------------------------------------------------------

    mpesa_transaction.processing_status = "failed"
    mpesa_transaction.processed_at = timezone.now()
    mpesa_transaction.save(
        update_fields=[
            "processing_status",
            "processed_at",
        ]
    )

    return {
        "success": False,
        "message": "Unsupported payment type.",
        "transaction_id": mpesa_transaction.id,
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
    
