import africastalking

username = "sandbox"
api_key = "atsk_130e7ff633dc0ccf19457be3c9f76b56a76ee16fb4c676dba4728f4a2546d09efdc29660"

africastalking.initialize(
    username,
    api_key
)

sms = africastalking.SMS

try:

    response = sms.send(
        "Nexavo SMS test successful.",
        ["+254791018986"]
    )

    print(response)

except Exception as e:

    print(
        f"Error: {e}"
    )
