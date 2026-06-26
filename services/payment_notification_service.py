def build_payment_confirmation_message(
    payment
):

    client = payment.client

    return (
        f"Dear {client.name}, payment of KES {payment.amount} received "
        f"for Nexavo Acc: {client.account_number}. "
        f"Bal: KES {client.wallet_balance:.2f}. "
        f"Thank you. Help: 0791018986"
    )