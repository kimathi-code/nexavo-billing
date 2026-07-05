from django import forms


class PortalActivationForm(
    forms.Form
):

    account_number = forms.CharField(
        max_length=20,
        label="Account Number"
    )

    phone_number = forms.CharField(
        max_length=20,
        label="Phone Number"
    )

    username = forms.CharField(
        max_length=50
    )

    password = forms.CharField(
        widget=forms.PasswordInput
    )
