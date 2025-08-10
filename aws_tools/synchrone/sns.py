"""
This module was automatically generated from aws_tools.asynchrone.sns
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from aws_tools.asynchrone.sns import aws_tools, base64, aiohttp, get_session, padding, hashes, load_pem_x509_certificate, Certificate, default_backend, urlparse, BaseModel, Literal, Annotated, Union, session, HEADERS, SNSSubscriptionConfirmationRequest, SNSNotificationRequest, SNSUnsubscribeRequest, SNSEventsTypes, send_sms_async, verify_sns_signature_async


def send_sms(phone_number: str, message: str):
    """
        
    """
    return _run_async(send_sms_async(phone_number=phone_number, message=message))


def verify_sns_signature(body: Union[aws_tools.asynchrone.sns.SNSSubscriptionConfirmationRequest, aws_tools.asynchrone.sns.SNSNotificationRequest, aws_tools.asynchrone.sns.SNSUnsubscribeRequest]) -> bool:
    """
    Verify the signature of an SNS message
    https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
    """
    return _run_async(verify_sns_signature_async(body=body))
