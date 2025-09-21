"""
This module was automatically generated from aws_tools.asynchrone.ses
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from typing import Iterable, Iterator
from aws_tools.asynchrone.ses import __name__, __doc__, __package__, __loader__, __spec__, __file__, __cached__, __builtins__, BaseModel, Field, ConfigDict, Literal, Union, get_session, MIMEMultipart, MIMEText, MIMEApplication, session, send_email_async, send_raw_email_async, _SESEvent, Mail, Recipient, BounceEvent, ComplaintEvent, DeliveryEvent, SendEvent, RejectEvent, OpenEvent, ClickEvent, RenderingFailureEvent, DeliveryDelayEvent, SubscriptionEvent, SESEmailEvent


def send_email(
        sender_email: str,
        recipient_emails: list[str],
        subject: str,
        body: str,
        configuration_set: str | None = None,
    ):
    """
    Send an email to the given recipients
    """
    return _run_async(send_email_async(sender_email=sender_email, recipient_emails=recipient_emails, subject=subject, body=body, configuration_set=configuration_set))


def send_raw_email(
    sender_email: str,
    recipient_emails: list[str],
    subject: str,
    text: str | None = None,
    html: str | None = None,
    attachments: dict[str, bytes] = {},
    configuration_set: str | None = None,
):
    """
    Send an email with optional file attachments via AWS SES
    """
    return _run_async(send_raw_email_async(sender_email=sender_email, recipient_emails=recipient_emails, subject=subject, text=text, html=html, attachments=attachments, configuration_set=configuration_set))
