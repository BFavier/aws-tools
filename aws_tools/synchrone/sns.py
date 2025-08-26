"""
This module was automatically generated from aws_tools.asynchrone.sns
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from typing import Iterable, Iterator
from aws_tools.asynchrone.sns import __name__, __doc__, __package__, __loader__, __spec__, __file__, __cached__, __builtins__, aws_tools, base64, aiohttp, get_session, padding, hashes, load_pem_x509_certificate, Certificate, default_backend, InvalidSignature, urlparse, BaseModel, Literal, Annotated, Union, session, HEADERS, _SNSEvents, SNSSubscriptionConfirmationRequest, SNSNotificationRequest, SNSUnsubscribeRequest, SNSEventsTypes, send_sms_async, _is_valid_cert_url, _get_signed_string, _get_signing_certificate_async, verify_sns_signature_async


def send_sms(phone_number: str, message: str):
    return _run_async(send_sms_async(phone_number=phone_number, message=message))


def verify_sns_signature(body: SNSEventsTypes) -> bool:
    """
    Verify the signature of an SNS message
    https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
    """
    return _run_async(verify_sns_signature_async(body=body))
