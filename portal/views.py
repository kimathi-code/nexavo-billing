from django.shortcuts import (
    render,
    redirect
)

from django.contrib import messages

from .forms import (
    PortalActivationForm
)

from .portal_activation_service import (
    activate_portal_account
)


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
                    "Portal account activated successfully."
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
