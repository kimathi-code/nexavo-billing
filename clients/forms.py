from django import forms
from .models import Client, Subscription, Package, Payment

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'phone', 'email', 'location', 'pppoe_username']

class SubscriptionForm(forms.ModelForm):
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Subscription
        fields = ['client', 'package']


class PaymentForm(forms.ModelForm):

    account_number = forms.CharField(
        max_length=20
    )

    class Meta:

        model = Payment

        fields = [
            'account_number',
            'amount',
            'transaction_code',
            'payment_method'
        ]