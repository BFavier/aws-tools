"""
Defines the payload format for bounce or complaints received by the API hook when an AWS SES mail gets bounced or a complaint.
Format documentation found here:
https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html
You can find some examples here:
https://docs.aws.amazon.com/ses/latest/dg/notification-examples.html
"""
import boto3
from pydantic import BaseModel, Field
from typing import Literal


ses = boto3.client("ses")


def send_email(sender_email: str, recipient_emails: list[str], subject: str, body: str):
    """
    """
    ses.send_email(
        Source=sender_email,
        Destination={
            'ToAddresses': recipient_emails,
        },
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body},}
        }
    )


class Mail(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#mail-object
    """

    class Header(BaseModel):
        name: str
        value: str

    class CommonHeader(BaseModel):
        _from: list[str] = Field(alias="from")
        date: str
        to: list[str]
        messageId: str
        subject: str

    timestamp: str
    messageId: str
    source: str
    sourceArn: str
    sourceIp: str
    sendingAccountId: str
    callerIdentity: str
    destination: str
    headersTruncated: bool | None = None
    headers: list[Header] | None = None
    commonHeaders: list[CommonHeader] | None = None


class Recipient(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#complained-recipients
    """
    emailAddress: str


class Bounce(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#bounce-object
    """

    class BounceRecipient(Recipient):
        """
        https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#bounced-recipients
        """
        action: str | None = None
        status: str | None = None
        diagnosticCode: str | None = None

    # for bounce type and subtype meanings, see https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#bounce-types
    bounceType: Literal["Undetermined", "Permanent", "Transient"]
    bounceSubType: Literal["Undetermined", "General", "NoEmail", "Suppressed", "OnAccountSuppressionList", "MailboxFull", "MessageTooLarge", "ContentRejected", "AttachmentRejected"]
    bouncedRecipients: list[BounceRecipient]
    timestamp: str
    feedbackId: str
    remoteMtaIp: str | None = None
    reportingMTA: str | None = None


class Complaint(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#complaint-object
    """

    complainedRecipients: list[Recipient]
    timestamp: str
    feedbackId: str
    # for complaint types, see https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#complaint-types
    complaintSubType: Literal["abuse", "auth-failure", "fraud", "not-spam", "other", "virus"]


class Delivery:
    """
    https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#delivery-object
    """
    timestamp: str
    processingTimeMillis: int
    recipients: list[Recipient]
    smtpResponse: str
    reportingMTA: str
    remoteMtaIp: str


class BounceOrComplaint(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html#top-level-json-object
    """
    notificationType: Literal["Bounce", "Complaint", "Delivery"]
    mail: Mail
    bounce: Bounce | None = None
    complaint: Complaint | None = None
    delivery: Delivery | None = None
