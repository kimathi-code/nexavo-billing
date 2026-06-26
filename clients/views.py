from decimal import Decimal
import logging
from django.views.decorators.http import require_POST
import json
from services.mpesa_service import MpesaService
from django.shortcuts import render, redirect
from .forms import ClientForm, SubscriptionForm, PaymentForm
from .models import Client, Subscription, Payment, StkPushRequest
from django.shortcuts import get_object_or_404
from datetime import date
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from services.mpesa_service import (
    process_payment_transaction,
    extract_mpesa_data
)

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.db.models import Sum

logger = logging.getLogger(
    "mpesa"
)

@staff_member_required
def create_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)

            client.created_by = request.user

            client.save()
            return redirect('client_success')
    else:
        form = ClientForm()

    return render(request, 'clients/create_client.html', {'form': form})


def client_success(request):
    return render(request, 'clients/success.html')



def client_list(request):

    query = request.GET.get('q')

    clients = Client.objects.all().order_by('-created_at')

    if query:

        clients = clients.filter(

            Q(name__icontains=query) |
            Q(account_number__icontains=query) |
            Q(phone__icontains=query)
        )

    return render(
        request,
        'clients/client_list.html',
        {
            'clients': clients
        }
    )


#edit existing client
@staff_member_required
def edit_client(request, id):
    client = get_object_or_404(Client, id=id)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            client = form.save(commit=False)

            client.updated_by = request.user

            client.save()
            return redirect('client_list')
    else:
        form = ClientForm(instance=client)

    return render(request, 'clients/edit_client.html', {'form': form})

#delete an existing client
@staff_member_required
def delete_client(request, id):
    client = get_object_or_404(Client, id=id)

    if request.method == 'POST':
        client.delete()
        return redirect('client_list')

    return render(request, 'clients/delete_client.html', {'client': client})

#subscription views
@staff_member_required
def create_subscription(request):
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('client_list')
    else:
        form = SubscriptionForm()

    return render(request, 'clients/create_subscription.html', {'form': form})

#active clients views
def active_clients(request):

    active_subscriptions = Subscription.objects.filter(
        end_date__gte=date.today()
    )

    return render(
        request,
        'clients/subscription_list.html',
        {
            'subscriptions': active_subscriptions,
            'title': 'Active Clients'
        }
    )


#expired clients views

def expired_clients(request):

    expired_subscriptions = Subscription.objects.filter(
        end_date__lt=date.today()
    )

    return render(
        request,
        'clients/subscription_list.html',
        {
            'subscriptions': expired_subscriptions,
            'title': 'Expired Clients'
        }
    )

#clients with no subscription views

def no_subscription_clients(request):

    clients = Client.objects.filter(subscription__isnull=True)

    return render(
        request,
        'clients/no_subscription.html',
        {
            'clients': clients
        }
    )

#payment views
@login_required
def create_payment(request):

    if request.method == 'POST':

        form = PaymentForm(request.POST)

        if form.is_valid():

            account_number = (
                form.cleaned_data[
                    'account_number'
                ]
            )

            try:

                client = Client.objects.get(
                    account_number=account_number
                )

            except Client.DoesNotExist:

                form.add_error(
                    'account_number',
                    'Client not found'
                )

                return render(
                    request,
                    'clients/create_payment.html',
                    {'form': form}
                )

            payment = form.save(commit=False)

            payment.client = client

            payment.save()

            return redirect('client_list')

    else:

        form = PaymentForm()

    return render(
        request,
        'clients/create_payment.html',
        {'form': form}
    )

@login_required
def billing_dashboard(request):

    total_clients = Client.objects.count()

    active_count = Subscription.objects.filter(
        status='active'
    ).count()

    expired_count = Subscription.objects.filter(
        status='expired'
    ).count()

    suspended_count = Subscription.objects.filter(
        status='suspended'
    ).count()

    clients_with_credit_count = Client.objects.filter(
        wallet_balance__gt=0
    ).count()

    total_wallet_balance = (
        Client.objects.aggregate(
            total=Sum('wallet_balance')
        )['total']
        or 0
    )

    clients_with_credit = Client.objects.filter(
        wallet_balance__gt=0
    ).order_by('-wallet_balance')

    expired_clients = []

    expired_subscriptions = Subscription.objects.filter(
        end_date__lt=date.today()
    ).select_related(
        'client',
        'package'
    )

    for subscription in expired_subscriptions:

        package_price = (
            subscription.package.price
            if subscription.package
            else 0
        )

        wallet_balance = (
            subscription.client.wallet_balance
        )

        outstanding_balance = (
            package_price - wallet_balance
        )

        if outstanding_balance < 0:
            outstanding_balance = 0

        expired_clients.append({
            'client': subscription.client,
            'subscription': subscription,
            'package_price': package_price,
            'wallet_balance': wallet_balance,
            'outstanding_balance': outstanding_balance,
        })

    context = {
        'total_clients': total_clients,
        'active_count': active_count,
        'expired_count': expired_count,
        'suspended_count': suspended_count,
        'clients_with_credit_count': clients_with_credit_count,
        'total_wallet_balance': total_wallet_balance,
        'clients_with_credit': clients_with_credit,
        'expired_clients': expired_clients,
    }

    return render(
        request,
        'clients/billing_dashboard.html',
        context
    )

# STK PUSH INITIATION VIEW
@csrf_exempt  
@require_POST
def initiate_stk_push_view(request):
    try:
        data = json.loads(request.body)
        account_number = data.get("account_number")
        amount = data.get("amount")

        if not account_number or not amount:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Account number and amount are required."
                },
                status=400
            )

        # Retrieve client record
        client = Client.objects.get(account_number=account_number)

        # Fire off payment initiation
        mpesa_service = MpesaService()
        result = mpesa_service.initiate_stk_push(client, amount)
        
        # Determine status code based on service response success flag
        status_code = 200 if result.get("success") else 400
        return JsonResponse(result, status=status_code)

    except Client.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Client not found."
            },
            status=404
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid JSON payload format."
            },
            status=400
        )
    except Exception as e:
        logger.exception("Error in initiate_stk_push_view")
        return JsonResponse(
            {
                "success": False,
                "message": "An unexpected error occurred processing your request."
            },
            status=500
        )

# CALLBACK VIEW FOR STK PUSH
@csrf_exempt
def stk_push_callback(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "ResultCode": 1,
                "ResultDesc": "POST requests only"
            },
            status=405
        )
    # Safaricom sends a JSON payload in the request body, so we need to parse it
    try:

        data = json.loads(
            request.body.decode("utf-8")
        )

        logger.info(
            "===== STK CALLBACK ====="
        )

        logger.info(data)

        # Safely extract the necessary fields from the callback data
        callback = data.get(
            "Body",
            {}
        ).get(
            "stkCallback",
            {}
        )
        # safely extract the identifiers and result code
        checkout_request_id = callback.get(
            "CheckoutRequestID"
        )

        merchant_request_id = callback.get(
            "MerchantRequestID"
        )

        result_code = int(
            callback.get(
                "ResultCode",
                -1
            )
        )

        result_desc = callback.get(
            "ResultDesc"
        )
        # find the corresponding StkPushRequest in the database
        stk_request = (
            StkPushRequest.objects.filter(
                checkout_request_id=checkout_request_id
            ).first()
        )
        # if the request is not found, return a success response to Safaricom to avoid retries
        if not stk_request:

            logger.warning(
                f"Unknown CheckoutRequestID: "
                f"{checkout_request_id}"
            )

            return JsonResponse(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted"
                }
            )
        # save the raw callback data for auditing purposes
        stk_request.raw_response = data

        # if customer canceled the transaction, update the status accordingly
        if result_code == 1032:

            stk_request.status = "cancelled"

            stk_request.response_description = result_desc

            stk_request.raw_response = data

            stk_request.save(
                update_fields=[
                    "status",
                    "response_description",
                    "raw_response",
                    "updated_at",
                ]
            )

            logger.info(
                f"Customer cancelled STK Push "
                f"{checkout_request_id}"
            )

            return JsonResponse(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted"
                }
            )
        # failed transaction, update the status and log the error
        if result_code != 0:

            stk_request.status = "failed"

            stk_request.response_description = result_desc

            stk_request.raw_response = data

            stk_request.save(
                update_fields=[
                    "status",
                    "response_description",
                    "raw_response",
                    "updated_at",
                ]
            )

            logger.warning(
                f"STK Push failed: "
                f"{result_desc}"
            )

            return JsonResponse(
                {
                    "ResultCode": 0,
                    "ResultDesc": "Accepted"
                }
            )
        # successful transaction, extact metadata and update the status
        metadata = callback.get(
            "CallbackMetadata",
            {}
        ).get(
            "Item",
            []
        )
        # helper variable to store the extracted values
        values = {

            item["Name"]: item.get("Value")

            for item in metadata if "Name" in item
        }

        amount = Decimal(
            str(
                values.get("Amount")
            )
        )

        receipt = values.get(
            "MpesaReceiptNumber"
        )

        phone_raw = values.get("PhoneNumber")
        phone = str(phone_raw) if phone_raw else ""

        # update & save the StkPushRequest with the successful transaction details
        stk_request.status = "completed"
        stk_request.response_description = result_desc
        stk_request.raw_response = data
        stk_request.save(
            update_fields=[
                "status",
                "response_description",
                "raw_response",
                "updated_at",
            ]
        )

        # feed the billing engine with the successful payment details
        result = process_payment_transaction(

            receipt_number=receipt,

            account_reference=stk_request.account_reference,

            phone_number=phone,

            amount=amount,

            payload=data
        )

        logger.info(
            f"STK payment processed successfully | "
            f"CheckoutID: {checkout_request_id} | "
            f"Receipt: {receipt} | "
            f"MerchantRequestID: {merchant_request_id} | "
            f"Billing Engine Result: {result}"
        )

        logger.info(
            "===== END STK CALLBACK ====="
        )
        return JsonResponse(
            {
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        )
    except Exception:

        logger.exception(
            "STK Callback Error"
        )

        return JsonResponse(
            {
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        ) 

#CALLBACK VIEW FOR MPESA PAYBILL
@csrf_exempt
def mpesa_callback(request):
    if request.method != "POST":

        return JsonResponse(
            {
                "ResultCode":1,
                "ResultDesc":"POST requests only"
            },
            status=405
        )

    try:

        data = json.loads(
            request.body.decode("utf-8")
        )

        logger.info(
            "===== M-PESA CALLBACK ====="
        )

        logger.info(data)

        payment_data = (
            extract_mpesa_data(data)
        )

        if not payment_data:

            return JsonResponse(
                {
                    "ResultCode": 1,
                    "ResultDesc": (
                        "Invalid Payload"
                    )
                }
            )

        result = (
            process_payment_transaction(

                receipt_number=payment_data[
                    "receipt_number"
                ],

                account_reference=payment_data[
                    "account_reference"
                ],

                phone_number=payment_data[
                    "phone_number"
                ],

                amount=payment_data[
                    "amount"
                ],

                payload=data
            )
        )

        logger.info(result)

        logger.info(
            "===== END CALLBACK ====="
        )

        return JsonResponse(
            {
                "ResultCode": 0,
                "ResultDesc": "Accepted"
            }
        )

    except Exception as e:

        logger.exception(
            f"Callback Error: {e}"
        )

        return JsonResponse(
            {
                "ResultCode": 1,
                "ResultDesc": "Error"
            }
        )
    