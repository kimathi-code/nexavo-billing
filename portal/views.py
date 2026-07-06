from django.shortcuts import (
    render,
    redirect
)

from django.contrib import messages

from django.core.exceptions import ValidationError

from django.contrib.auth import authenticate, login

from django.contrib.auth.decorators import login_required

from .forms import (
    PortalActivationForm
)

from .portal_activation_service import (
    activate_portal_account
)

# Portal activation view
def portal_activation_view(
    request
):

    if request.method == "POST":

        form = PortalActivationForm(
            request.POST
        )

        if form.is_valid():

            try:

                activate_portal_account(
                    form.cleaned_data["account_number"],
                    form.cleaned_data["phone_number"],
                    form.cleaned_data["username"],
                    form.cleaned_data["password"],
                )


                messages.success(
                    request,
                    "Portal account activated successfully. Please log in to access your dashboard."
                )

                return redirect(
                    "portal_login"
                )


            except ValidationError as error:
                # Safely parse the validation error string
                error_msg = error.messages[0] if hasattr(error, 'messages') else str(error)

                # Account is already active -> notify user and redirect to login
                messages.info(
                    request,
                    f"{error_msg} Please log in to continue."
                )
                return redirect(
                    "portal_login"
                )


            except Exception:

                messages.error(
                    request,
                    "Activation failed. Please check your details."
                )


    else:

        form = PortalActivationForm()


    return render(
        request,
        "portal/portal_activation.html",
        {
            "form": form
        }
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
