"""
Here below the documentation of the expected payload format for the API route handling SNS topic subscription :
https://docs.aws.amazon.com/sns/latest/dg/sns-message-and-json-formats.html
"""
import aws_tools
import base64
import aiohttp
from aiobotocore.session import get_session
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.x509 import load_pem_x509_certificate, Certificate
from cryptography.hazmat.backends import default_backend
from urllib.parse import urlparse
from pydantic import BaseModel
from typing import Literal, Annotated, Union


session = get_session()


# custome sns headers, dcoumented here: https://docs.aws.amazon.com/sns/latest/dg/http-header.html
HEADERS = [
    "x-amz-sns-message-type",  # 'Notification', 'SubscriptionConfirmation', 'UnsubscribeConfirmation'
    "x-amz-sns-message-id",  # '165545c9-2a5c-472c-8df2-7ff2be2b3b1b3'
    "x-amz-sns-topic-arn",  # 'arn:aws:sns:us-west-2:123456789012:MyTopic'
    "x-amz-sns-subscription-arn"  # 'arn:aws:sns:us-west-2:123456789012:MyTopic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55'
]


class _SNSEvents(BaseModel):
    pass


class SNSSubscriptionConfirmationRequest(_SNSEvents):
    """
    https://docs.aws.amazon.com/sns/latest/dg/http-subscription-confirmation-json.html
    """
    Type: Literal["SubscriptionConfirmation"]
    MessageId: Annotated[str, "165545c9-2a5c-472c-8df2-7ff2be2b3b1b"]
    Token: Annotated[str, "2336412f37..."]
    TopicArn: Annotated[str, "arn:aws:sns:us-west-2:123456789012:MyTopic"]
    Message: Annotated[str, ""]
    SubscribeURL: Annotated[str, ""]
    Timestamp: Annotated[str, ""]
    SignatureVersion: Annotated[str, "1"]
    Signature: Annotated[str, "EXAMPLEpH+DcEwjAPg8O9mY8dReBSwksfg2S7WKQcikcNKWLQjwu6A4VbeS0QHVCkhRS7fUQvi2egU3N858fiTDN6bkkOxYDVrY0Ad8L10Hs3zH81mtnPk5uvvolIC1CXGu43obcgFxeL3khZl8IKvO61GWB6jI9b5+gLPoBc1Q="]
    SigningCertURL: Annotated[str, "https://sns.us-west-2.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem"]


class SNSNotificationRequest(_SNSEvents):
    """
    https://docs.aws.amazon.com/sns/latest/dg/http-notification-json.html
    """
    Type: Literal["Notification"]
    MessageId: Annotated[str, "22b80b92-fdea-4c2c-8f9d-bdfb0c7bf324"]
    TopicArn: Annotated[str, "arn:aws:sns:us-west-2:123456789012:MyTopic"]
    Subject: Annotated[str, "My First Message"]
    Message: Annotated[str, "Hello world!"]
    Timestamp: Annotated[str, "2012-05-02T00:54:06.655Z"]
    SignatureVersion: Annotated[str, "1"]
    Signature: Annotated[str, "EXAMPLEw6JRN..."]
    SigningCertURL: Annotated[str, "https://sns.us-west-2.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem"]
    UnsubscribeURL: Annotated[str, "https://sns.us-west-2.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-west-2:123456789012:MyTopic:c9135db0-26c4-47ec-8998-413945fb5a96"]


class SNSUnsubscribeRequest(_SNSEvents):
    """
    https://docs.aws.amazon.com/sns/latest/dg/http-unsubscribe-confirmation-json.html
    """
    Type: Literal["UnsubscribeConfirmation"]
    MessageId: Annotated[str, "47138184-6831-46b8-8f7c-afc488602d7d"]
    Token: Annotated[str, "2336412f37..."]
    TopicArn: Annotated[str, "arn:aws:sns:us-west-2:123456789012:MyTopic"]
    Message: Annotated[str, "You have chosen to deactivate subscription arn:aws:sns:us-west-2:123456789012:MyTopic:2bcfbf39-05c3-41de-beaa-fcfcc21c8f55.\nTo cancel this operation and restore the subscription, visit the SubscribeURL included in this message."]
    SubscribeURL: Annotated[str, "https://sns.us-west-2.amazonaws.com/?Action=ConfirmSubscription&TopicArn=arn:aws:sns:us-west-2:123456789012:MyTopic&Token=2336412f37fb6..."]
    Timestamp: Annotated[str, "2012-04-26T20:06:41.581Z"]
    SignatureVersion: Annotated[str, "1"]
    Signature: Annotated[str, "EXAMPLEHXgJm..."]
    SigningCertURL: Annotated[str, "https://sns.us-west-2.amazonaws.com/SimpleNotificationService-f3ecfb7224c7233fe7bb5f59f96de52f.pem"]


SNSEventsTypes = Union[SNSSubscriptionConfirmationRequest, SNSNotificationRequest, SNSUnsubscribeRequest]
assert set(_SNSEvents.__subclasses__()) == set(SNSEventsTypes.__args__)


async def send_sms_async(phone_number: str, message: str):
    """
    """
    async with session.create_client("sns") as sns:
        await sns.publish(
            PhoneNumber=phone_number,
            Message=message
        )


def _is_valid_cert_url(cert_url: str) -> bool:
    """
    Verify that the SigningCertURL is a valid AWS URL
    """
    parsed = urlparse(cert_url)
    return (parsed.scheme == "https" and
            parsed.hostname and
            parsed.hostname.endswith(".amazonaws.com"))


def _get_signed_string(message: SNSEventsTypes) -> str:
    """
    Construct the string that was originally signed
    https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message-verify-message-signature.html
    """
    fields_to_sign = ("Message", "MessageId", "SubscribeURL", "Subject", "Timestamp", "TopicArn", "Type")
    field_values = ((field, getattr(message, field, None)) for field in fields_to_sign)
    string_to_sign = "\n".join(f"{field}\n{value}" for field, value in field_values if value is not None)
    return string_to_sign


async def _get_signing_certificate_async(cert_url: str) -> Certificate:
    """
    Download the certificate from the SigningCertURL
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(cert_url) as response:
            cert_data = await response.read()
    return load_pem_x509_certificate(cert_data, default_backend())


async def verify_sns_signature_async(body: SNSEventsTypes) -> bool:
    """
    Verify the signature of an SNS message
    https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
    """
    if not _is_valid_cert_url(body.SigningCertURL):
        return False
    decoded_signature = base64.b64decode(body.Signature)
    cert = await _get_signing_certificate_async(body.SigningCertURL)
    public_key = cert.public_key()
    if body.SignatureVersion == "1":
        hash = hashes.SHA1()
    elif body.SignatureVersion == "2":
        hash = hashes.SHA256()
    else:
        raise RuntimeError(f"Unexpected signature version '{body.SignatureVersion}'")
    try:
        public_key.verify(
            decoded_signature,
            _get_signed_string(body).encode("utf-8"),
            padding.PKCS1v15(),
            hash
        )
    except Exception as e:
        return False
    else:
        return True
