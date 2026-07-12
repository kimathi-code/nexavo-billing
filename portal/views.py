from django.shortcuts import (
    render,
    redirect
)

from django.contrib import messages

from django.core.exceptions import ValidationError

from django.contrib.auth import authenticate, login

from django.contrib.auth.decorators import login_required

from clients.models import Client

from .forms import (
    PortalActivationRequestForm,
    PortalActivationConfirmForm,
    PortalPasswordResetRequestForm,
    PortalPasswordResetConfirmForm
)

from .portal_otp_service import (
    send_portal_activation_otp,
    verify_portal_activation_otp,
    send_portal_otp,
    verify_portal_otp
)

from .portal_activation_service import (
    activate_portal_account
)

# Portal activation view
def portal_activation_view(request):

    client_id = request.session.get(
        "activation_client_id"
    )


    # Stage 2: OTP verification + account creation
    if client_id:

        form = PortalActivationConfirmForm(
            request.POST or None
        )


        if request.method == "POST" and form.is_valid():

            try:
                client = Client.objects.get(
                    id=client_id
                )

                # 1. Verify OTP first
                verify_portal_activation_otp(
                    client=client,
                    code=form.cleaned_data["otp_code"]
                )

                # 2. Complete Account Activation
                activate_portal_account(
                    client=client,
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"]
                )

                # 3. Clean up session payload on success
                request.session.pop(
                    "activation_client_id",
                    None
                )


                messages.success(
                    request,
                    "Portal activated successfully. Please log in."
                )


                return redirect(
                    "portal_login"
                )

            except Client.DoesNotExist:
                request.session.pop(
                    "activation_client_id",
                    None
                )
                messages.error(request, "Session invalid. Please restart activation.")
                return redirect("portal_activation")

            except ValidationError as error:

                error_msg = (
                    error.messages[0]
                    if hasattr(error, "messages")
                    else str(error)
                )
                # Check if error indicates account is already active
                if "already activated" in error_msg.lower():
                    request.session.pop(
                        "activation_client_id",
                        None
                    )
                    messages.info(request, f"{error_msg} Please sign in.")
                    return redirect("portal_login")

                # For invalid/expired OTP errors, keep them on Stage 2 to retry
                messages.error(request, error_msg)
                return render(
                    request,
                    "portal/portal_activation.html",
                    {"form": form, "stage": "confirm"}
                )

        # Initial GET request handling for Stage 2
        return render(
            request,
            "portal/portal_activation.html",
            {
                "form": form,
                "stage": "confirm"
            }
        )



    # Stage 1: Account verification + send OTP

    form = PortalActivationRequestForm(
        request.POST or None
    )


    if request.method == "POST" and form.is_valid():

        try:

            client = Client.objects.get(
                account_number=form.cleaned_data["account_number"],
                phone=form.cleaned_data["phone"]
            )

            # Fire off OTP via service layer
            send_portal_activation_otp(
                client
            )

            # Set session anchor
            request.session[
                "activation_client_id"
            ] = client.id


            messages.success(
                request,
                "Verification code sent to your phone."
            )


            return redirect(
                "portal_activation"
            )


        except Client.DoesNotExist:

            messages.error(
                request,
                "Customer account not found."
            )


    return render(
        request,
        "portal/portal_activation.html",
        {
            "form": form,
            "stage": "request"
        }
    )

#resend activation code view
def portal_activation_resend_code(request):

    client_id = request.session.get(
        "activation_client_id"
    )


    if not client_id:

        messages.error(
            request,
            "Please restart activation."
        )

        return redirect(
            "portal_activation"
        )


    try:

        client = Client.objects.get(
            id=client_id
        )


        send_portal_activation_otp(
            client
        )


        messages.success(
            request,
            "A new verification code has been sent."
        )


    except Client.DoesNotExist:

        request.session.pop(
            "activation_client_id",
            None
        )


        messages.error(
            request,
            "Session expired. Please restart activation."
        )


    return redirect(
        "portal_activation"
    )

# Portal login view 
def portal_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("portal_dashboard")

        messages.error(request, "Invalid username or password.")

    return render(
        request,
        "portal/portal_login.html"
    )

# Portal dashboard view
@login_required
def portal_dashboard(request):
    return render(
        request,
        "portal/portal_dashboard.html"
    )

# Portal password reset view
def portal_password_reset(request):

    client_id = request.session.get(
        "password_reset_client_id"
    )


    # Stage 2: OTP confirmation + password change

    if client_id:

        form = PortalPasswordResetConfirmForm(
            request.POST or None
        )


        if request.method == "POST" and form.is_valid():

            try:

                client = Client.objects.get(
                    id=client_id
                )


                verify_portal_otp(
                    client=client,
                    code=form.cleaned_data["otp_code"],
                    purpose="password_reset"
                )


                portal_account = client.portal_account


                user = portal_account.user


                user.set_password(
                    form.cleaned_data["new_password"]
                )


                user.save()


                request.session.pop(
                    "password_reset_client_id",
                    None
                )


                messages.success(
                    request,
                    "Password changed successfully. Please login."
                )


                return redirect(
                    "portal_login"
                )


            except ValidationError as error:

                error_msg = (
                    error.messages[0]
                    if hasattr(error, "messages")
                    else str(error)
                )


                messages.error(
                    request,
                    error_msg
                )


            except Client.DoesNotExist:

                request.session.pop(
                    "password_reset_client_id",
                    None
                )


                messages.error(
                    request,
                    "Session expired. Please restart password reset."
                )


                return redirect(
                    "portal_password_reset"
                )


        return render(
            request,
            "portal/portal_password_reset.html",
            {
                "form": form,
                "stage": "confirm"
            }
        )



    # Stage 1: verify customer

    form = PortalPasswordResetRequestForm(
        request.POST or None
    )


    if request.method == "POST" and form.is_valid():

        try:

            client = Client.objects.get(
                account_number=form.cleaned_data["account_number"],
                phone=form.cleaned_data["phone"]
            )


            send_portal_otp(
                client=client,
                purpose="password_reset"
            )


            request.session[
                "password_reset_client_id"
            ] = client.id


            messages.success(
                request,
                "Password reset code sent."
            )


            return redirect(
                "portal_password_reset"
            )


        except Client.DoesNotExist:

            messages.error(
                request,
                "Customer account not found."
            )


    return render(
        request,
        "portal/portal_password_reset.html",
        {
            "form": form,
            "stage": "request"
        }
    )

def portal_password_reset_restart(request):

    request.session.pop(
        "password_reset_client_id",
        None
    )


    messages.info(
        request,
        "Password reset restarted. Please verify your account again."
    )


    return redirect(
        "portal_password_reset"
    )