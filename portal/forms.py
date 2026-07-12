from django import forms


class PortalActivationRequestForm(forms.Form):
    account_number = forms.CharField(
        max_length=20
    )

    phone = forms.CharField(
        max_length=20
    )


class PortalActivationConfirmForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6
    )

    username = forms.CharField(
        max_length=150
    )

    password = forms.CharField(
        widget=forms.PasswordInput
    )

# password reset forms
class PortalPasswordResetRequestForm(forms.Form):

    account_number = forms.CharField(
        max_length=20
    )

    phone = forms.CharField(
        max_length=20
    )


class PortalPasswordResetConfirmForm(forms.Form):

    otp_code = forms.CharField(
        max_length=6
    )


    new_password = forms.CharField(
        widget=forms.PasswordInput
    )