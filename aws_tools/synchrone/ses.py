"""
This module was automatically generated from aws_tools.asynchrone.ses
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from aws_tools.asynchrone.ses import BaseModel, Field, ConfigDict, Literal, Union, get_session, session, send_email_async, Mail, Recipient, BounceEvent, ComplaintEvent, DeliveryEvent, SendEvent, RejectEvent, OpenEvent, ClickEvent, RenderingFailureEvent, DeliveryDelayEvent, SubscriptionEvent, SentEmailEvent, EventTypes


def send_email(sender_email: str, recipient_emails: list[str], subject: str, body: str):
    """
    Send an email to the given recipients
    """
    return _run_async(send_email_async(sender_email=sender_email, recipient_emails=recipient_emails, subject=subject, body=body))
