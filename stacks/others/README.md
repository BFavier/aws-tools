# Emailing stack

The emailing stack defines the resources so that your domain name can receive emails.

Here below a route that should exists in your backend to handle the mail bounce or complaints.

⚠️ This route will be called once at stack creation for the stack to create successfully. Your backend should be up and running and expose a such route.

```python
import json
import aiohttp
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.x509 import load_pem_x509_certificate, Certificate
from cryptography.hazmat.backends import default_backend
from urllib.parse import urlparse
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse


router = APIRouter()


@router.post("/mail-bounce-or-complaint/", include_in_schema=False)
async def mail_bounce_or_complaint_route(request: Request):
    """
    TODO: complete me
    This API route is called by AWS SNS service everytime an email is sent to a
    non-existing email or when a recipient marked one of our email as spam.
    This is also called once at emailing stack deployment to verify that the endpoint exists.
    """
    body = await request.json()
    if not (await verify_sns_signature(body)):
        raise HTTPException(403, "Invalid signature")
    # Handle topic subscription
    if body['Type'] == 'SubscriptionConfirmation':
        # Confirm the subscription
        subscribe_url = body['SubscribeURL']
        async with aiohttp.ClientSession() as session:
            async with session.get(subscribe_url) as response:
                if response.status >= 300:
                    raise HTTPException(401, "invalid subscription url")
        return JSONResponse(content={"message": "Subscription confirmed"})
    # Handle Notification
    elif body['Type'] == 'Notification':
        # Process the notification message
        notification_message = json.loads(body['Message'])
        # Perform actions based on the SNS message
        ...
        print(notification_message)
        ...
        return JSONResponse(content={"message": "Notification processed", "details": notification_message})
    else:
        raise HTTPException(404, "invalid request type")


async def verify_sns_signature(message) -> bool:
    """
    Verify the SNS message signature
    """
    if not is_valid_cert_url(message["SigningCertURL"]):
        return False
    decoded_signature = base64.b64decode(message["Signature"])
    cert = await _get_signing_certificate(message["SigningCertURL"])
    public_key = cert.public_key()
    try:
        public_key.verify(
            decoded_signature,
            _get_certificate_string_to_sign(message).encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA1()
        )
    except Exception as e:
        return False
    else:
        return True


def is_valid_cert_url(cert_url: str) -> bool:
    """
    Verify that the SigningCertURL is a valid AWS URL
    """
    parsed = urlparse(cert_url)
    return (parsed.scheme == "https" and
            parsed.hostname and
            parsed.hostname.endswith(".amazonaws.com"))


async def _get_signing_certificate(cert_url: str) -> Certificate:
    """
    Download the certificate from the SigningCertURL
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(cert_url) as response:
            cert_data = await response.read()
    return load_pem_x509_certificate(cert_data, default_backend())


def _get_certificate_string_to_sign(message: dict) -> str:
    """
    Construct the string that was originally signed
    """
    fields_to_sign = []
    if message["Type"] == "Notification":
        fields_to_sign = ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"]
    elif message["Type"] == "SubscriptionConfirmation":
        fields_to_sign = ["Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"]
    string_to_sign = ""
    for field in fields_to_sign:
        if field in message:
            string_to_sign += f"{field}\n{message[field]}\n"
    return string_to_sign

```