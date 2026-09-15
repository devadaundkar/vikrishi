from twilio.rest import Client

ACCOUNT_SID = "AC8440eac89f193be10f256f2ada607306"
AUTH_TOKEN = "4c70732581fc4e7e4dc7dd66e0ca4f30"
FROM_WHATSAPP_NUMBER = "whatsapp:+14155238886"
TO_WHATSAPP_NUMBER = "whatsapp:+918010949780"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

message = client.messages.create(
    body="Hi Your booking has been confirmed!!",
    from_=FROM_WHATSAPP_NUMBER,
    to=TO_WHATSAPP_NUMBER
)

print("SID:", message.sid)
print("Status:", message.status)
